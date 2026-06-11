#!/usr/bin/env python3
import json
import math
import os
import rospy
import yaml
import actionlib
from datetime import datetime

from geometry_msgs.msg import Quaternion, Twist, PoseWithCovarianceStamped
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from std_msgs.msg import String
from actionlib_msgs.msg import GoalStatus

ST_INIT   = "INIT"
ST_GO_TO  = "GO_TO_LOCATION"
ST_QR     = "QR_VERIFY"
ST_REPORT = "REPORT"
ST_NEXT   = "NEXT_LOCATION"
ST_FINISH = "FINISH"

SUCCESS = "SUCCESS"
FAIL    = "FAIL"
SKIPPED = "SKIPPED"


def yaw_to_quat(yaw):
    return Quaternion(x=0.0, y=0.0, z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0))

def fmt_sec(s):
    m, sec = divmod(int(s), 60)
    return f"{m}d {sec:02d}s" if m else f"{sec}s"


class TaskManager:
    def __init__(self):
        rospy.init_node("task_manager", anonymous=False)

        mission_file = rospy.get_param("~mission_file", "")
        if not mission_file:
            rospy.logfatal("[TaskManager] ~mission_file parametresi eksik!")
            raise SystemExit(1)

        with open(mission_file, "r") as f:
            cfg = yaml.safe_load(f)

        self.locations   = cfg["locations"]
        self.cfg         = cfg
        self.nav_retries = cfg.get("navigation_retries", 1)
        self.qr_retries  = cfg.get("qr_retries", 2)
        self.qr_timeout  = cfg.get("qr_scan_timeout", 10.0)

        self.results      = {}
        self.loc_times    = {}   # her nokta için (nav_sn, toplam_sn)
        self.current_idx  = 0
        self.state        = ST_INIT

        self._qr_data     = None
        self._mission_go  = False
        self._mission_t0  = None
        self._loc_t0      = None
        self._current_yaw = None   # AMCL'den anlık yaw

        self._cmd_pub    = rospy.Publisher("/cmd_vel", Twist, queue_size=1)
        self._status_pub = rospy.Publisher("/task_manager/status", String, queue_size=10)
        rospy.Subscriber("/qr_code/data", String, self._qr_cb, queue_size=5)
        rospy.Subscriber("/mission/start", String, self._start_cb, queue_size=1)
        rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, self._pose_cb, queue_size=5)

        rospy.loginfo("[TaskManager] move_base bekleniyor...")
        self.mb = actionlib.SimpleActionClient("move_base", MoveBaseAction)
        self.mb.wait_for_server(timeout=rospy.Duration(60.0))
        rospy.loginfo("[TaskManager] Hazır. GCS'den 'Görev Başlat' bekleniyor...")

    # ------------------------------------------------------------------ #

    def _pub_status(self, location=None, state=None, msg=None, level="info", report=None):
        payload = {}
        if location: payload["location"] = location
        if state:    payload["state"]    = state
        if msg:      payload["msg"]      = msg
        if report:   payload["report"]   = report
        payload["level"] = level
        self._status_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))

    def _qr_cb(self, msg):
        self._qr_data = msg.data.strip()

    def _pose_cb(self, msg):
        q = msg.pose.pose.orientation
        self._current_yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )

    def _start_cb(self, msg):
        if not self._mission_go:
            rospy.loginfo("[TaskManager] /mission/start alındı — görev başlıyor!")
            self._mission_go = True

    def _build_goal(self, loc):
        g = self.cfg[loc]["goal"]
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp    = rospy.Time.now()
        goal.target_pose.pose.position.x = g["x"]
        goal.target_pose.pose.position.y = g["y"]
        goal.target_pose.pose.orientation = yaw_to_quat(g["yaw"])
        return goal

    def _navigate(self, loc):
        timeout = self.cfg[loc].get("timeout", 90)
        for attempt in range(self.nav_retries + 1):
            if attempt:
                rospy.logwarn("[TaskManager] Navigasyon yeniden deneme %d/%d: %s",
                              attempt, self.nav_retries, loc)
            rospy.loginfo("[TaskManager] Hedefe gidiliyor: %s", loc)
            nav_t0 = rospy.Time.now()
            self.mb.send_goal(self._build_goal(loc))
            ok = self.mb.wait_for_result(rospy.Duration(timeout))
            nav_elapsed = (rospy.Time.now() - nav_t0).to_sec()
            if not ok:
                rospy.logwarn("[TaskManager] Timeout (%ds): %s", timeout, loc)
                self.mb.cancel_goal()
                continue
            if self.mb.get_state() == GoalStatus.SUCCEEDED:
                rospy.loginfo("[TaskManager] Hedefe ulaşıldı: %s (%.0fs)", loc, nav_elapsed)
                self.loc_times.setdefault(loc, {})["nav_sec"] = nav_elapsed
                # QR'ın göründüğü yöne dön
                self._align_to_yaw(self.cfg[loc]["goal"]["yaw"])
                return True
            rospy.logwarn("[TaskManager] Navigasyon başarısız (state=%d): %s",
                          self.mb.get_state(), loc)
        return False

    def _angle_diff(self, a, b):
        d = a - b
        while d >  math.pi: d -= 2 * math.pi
        while d < -math.pi: d += 2 * math.pi
        return d

    def _align_to_yaw(self, target_yaw, tol=0.15, timeout=10.0):
        """Robotu hedef yaw açısına hassas biçimde döndürür."""
        # AMCL'den yaw gelene kadar bekle
        for _ in range(20):
            if self._current_yaw is not None:
                break
            rospy.sleep(0.1)
        if self._current_yaw is None:
            rospy.logwarn("[TaskManager] AMCL yaw alınamadı, hizalama atlandı.")
            return

        rospy.loginfo("[TaskManager] Yön hizalanıyor → hedef yaw=%.2f rad", target_yaw)
        rate  = rospy.Rate(20)
        start = rospy.Time.now()
        while not rospy.is_shutdown():
            if (rospy.Time.now() - start).to_sec() > timeout:
                rospy.logwarn("[TaskManager] Yön hizalama timeout.")
                break
            err = self._angle_diff(target_yaw, self._current_yaw)
            if abs(err) < tol:
                rospy.loginfo("[TaskManager] Hizalama tamam (hata=%.3f rad).", err)
                break
            # Minimum hız yok — hedefe yaklaştıkça doğal yavaşlar, sallanmaz
            speed = min(0.6, abs(err) * 1.2)
            twist = Twist()
            twist.angular.z = math.copysign(speed, err)
            self._cmd_pub.publish(twist)
            rate.sleep()
        self._cmd_pub.publish(Twist())
        rospy.sleep(0.5)

    def _scan_qr(self, loc):
        """
        QR tarama stratejisi:
          1. Hedef yaw'da sabitle ve 3s bekle
          2. Bulamazsan ±50° küçük tarama yap
          3. qr_retries kadar tekrar
        """
        expected    = self.cfg[loc]["qr_expected"]
        target_yaw  = self.cfg[loc]["goal"]["yaw"]
        sweep_angle = math.radians(50)   # ±50°
        sweep_speed = 0.25               # rad/s

        for attempt in range(self.qr_retries + 1):
            if attempt:
                rospy.logwarn("[TaskManager] QR yeniden deneme %d/%d: %s",
                              attempt, self.qr_retries, loc)

            # ── Adım 1: hedef yöne hizala ve statik tara ──
            self._align_to_yaw(target_yaw)
            self._qr_data = None
            rospy.loginfo("[TaskManager] QR statik taranıyor (3s): %s", loc)
            rate     = rospy.Rate(10)
            deadline = rospy.Time.now() + rospy.Duration(3.0)
            while rospy.Time.now() < deadline and not rospy.is_shutdown():
                if self._qr_data is not None:
                    break
                rate.sleep()

            if self._qr_data is not None:
                rospy.loginfo("[TaskManager] Statik taramada QR bulundu.")
            else:
                # ── Adım 2: ±50° küçük tarama ──
                rospy.loginfo("[TaskManager] Küçük tarama ±50°: %s", loc)
                for direction in (+1, -1):
                    self._sweep(sweep_angle * direction, sweep_speed)
                    if self._qr_data is not None:
                        break
                # hedef yöne geri dön
                self._align_to_yaw(target_yaw)

            if self._qr_data is None:
                rospy.logwarn("[TaskManager] QR okunamadı: %s", loc)
                continue

            rospy.loginfo("[TaskManager] QR verisi: '%s' | beklenen: '%s'",
                          self._qr_data, expected)
            if self._qr_data == expected:
                rospy.loginfo("[TaskManager] DOĞRULANDI: %s", loc)
                return True
            rospy.logwarn("[TaskManager] QR eşleşmedi (yanlış kod): %s", loc)

        return False

    def _sweep(self, angle, speed):
        """Verilen açı kadar döner (+ saat yönü, - saat karşı) ve durur."""
        duration = abs(angle) / speed
        twist    = Twist()
        twist.angular.z = math.copysign(speed, angle)
        end  = rospy.Time.now() + rospy.Duration(duration)
        rate = rospy.Rate(10)
        while rospy.Time.now() < end and not rospy.is_shutdown():
            self._cmd_pub.publish(twist)
            if self._qr_data is not None:
                break
            rate.sleep()
        self._cmd_pub.publish(Twist())
        rospy.sleep(0.3)

    def _save_report(self, total_sec):
        now_str  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fname    = datetime.now().strftime("gorev_raporu_%Y%m%d_%H%M%S.txt")
        save_dir = os.path.expanduser("~/gorev_raporlari")
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, fname)

        ok    = sum(1 for r in self.results.values() if r == SUCCESS)
        total = len(self.locations)

        lines = []
        lines.append("=" * 58)
        lines.append("  SERVİS ROBOTU — GÖREV RAPORU")
        lines.append(f"  Tarih/Saat : {now_str}")
        lines.append(f"  Toplam süre: {fmt_sec(total_sec)}")
        lines.append("=" * 58)
        lines.append(f"  {'NOKTA':<14} {'SONUÇ':<10} {'NAV SÜRESİ':<12} {'TOPLAM'}")
        lines.append("-" * 58)
        for loc in self.locations:
            res  = self.results.get(loc, "BEKLEMEDE")
            icon = {SUCCESS: "✓", FAIL: "✗", SKIPPED: "⊘"}.get(res, "?")
            t    = self.loc_times.get(loc, {})
            nav  = fmt_sec(t.get("nav_sec", 0))
            tot  = fmt_sec(t.get("total_sec", 0))
            lines.append(f"  {icon} {loc:<13} {res:<10} {nav:<12} {tot}")
        lines.append("-" * 58)
        lines.append(f"  Başarılı: {ok}/{total}   Başarısız: {total - ok}/{total}")
        lines.append("=" * 58)

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        rospy.loginfo("[TaskManager] Rapor kaydedildi: %s", path)
        for l in lines:
            rospy.loginfo(l)

        return lines

    # ------------------------------------------------------------------ #

    def run(self):
        rospy.loginfo("[TaskManager] Hazır — GCS'den 'Görev Başlat' bekleniyor.")

        wait_rate = rospy.Rate(2)
        while not rospy.is_shutdown() and not self._mission_go:
            wait_rate.sleep()

        if rospy.is_shutdown():
            return

        self._mission_t0 = rospy.Time.now()
        rospy.loginfo("[TaskManager] Görev döngüsü başladı.")
        rate = rospy.Rate(1)

        while not rospy.is_shutdown():

            if self.state == ST_INIT:
                rospy.loginfo("[TaskManager] INIT: sistem kontrolü yapılıyor...")
                self.state = ST_GO_TO

            elif self.state == ST_GO_TO:
                if self.current_idx >= len(self.locations):
                    self.state = ST_FINISH
                    continue
                loc = self.locations[self.current_idx]
                self._loc_t0 = rospy.Time.now()
                rospy.loginfo("[TaskManager] GO_TO_LOCATION: %s", loc)
                self._pub_status(location=loc, state="GIDILIYOR",
                                 msg=f"{loc} hedefine gidiliyor")
                if self._navigate(loc):
                    self.state = ST_QR
                else:
                    rospy.logerr("[TaskManager] Navigasyon tamamen başarısız: %s", loc)
                    self.results[loc] = FAIL
                    elapsed = (rospy.Time.now() - self._loc_t0).to_sec()
                    self.loc_times.setdefault(loc, {})["total_sec"] = elapsed
                    self._pub_status(location=loc, state=FAIL,
                                     msg=f"{loc} hedefe ulaşılamadı", level="error")
                    self.state = ST_NEXT

            elif self.state == ST_QR:
                loc = self.locations[self.current_idx]
                rospy.loginfo("[TaskManager] QR_VERIFY: %s", loc)
                self._pub_status(location=loc, state="QR",
                                 msg=f"{loc} QR kodu taranıyor")
                self.results[loc] = SUCCESS if self._scan_qr(loc) else SKIPPED
                self.state = ST_REPORT

            elif self.state == ST_REPORT:
                loc = self.locations[self.current_idx]
                res = self.results[loc]
                elapsed = (rospy.Time.now() - self._loc_t0).to_sec()
                self.loc_times.setdefault(loc, {})["total_sec"] = elapsed
                rospy.loginfo("[TaskManager] REPORT: %s -> %s (%.0fs)", loc, res, elapsed)
                lvl = "ok" if res == SUCCESS else ("warn" if res == SKIPPED else "error")
                self._pub_status(location=loc, state=res,
                                 msg=f"{loc}: {res} ({fmt_sec(elapsed)})", level=lvl)
                self.state = ST_NEXT

            elif self.state == ST_NEXT:
                self.current_idx += 1
                self.state = ST_GO_TO

            elif self.state == ST_FINISH:
                total_sec = (rospy.Time.now() - self._mission_t0).to_sec()
                ok = sum(1 for r in self.results.values() if r == SUCCESS)
                report_lines = self._save_report(total_sec)
                self._pub_status(
                    msg=f"Görev bitti — {ok}/{len(self.locations)} başarılı | Süre: {fmt_sec(total_sec)}",
                    level="ok",
                    report="\n".join(report_lines))
                break

            rate.sleep()


if __name__ == "__main__":
    try:
        TaskManager().run()
    except rospy.ROSInterruptException:
        pass
