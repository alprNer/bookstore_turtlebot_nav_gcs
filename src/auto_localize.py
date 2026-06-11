#!/usr/bin/env python3
"""
Otomatik AMCL Lokalizasyon Node'u
- Robotun bilinen başlangıç konumunu /initialpose ile AMCL'e bildirir
- Partiküller doğrudan doğru bölgeye yoğunlaşır (global scatter yok)
- Kısa bir spin ile ince ayar yapılır
"""
import math
import rospy
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped, Quaternion


def yaw_to_quat(yaw):
    return Quaternion(x=0.0, y=0.0,
                      z=math.sin(yaw / 2.0),
                      w=math.cos(yaw / 2.0))


class AutoLocalizer:
    def __init__(self):
        rospy.init_node("auto_localizer", anonymous=False)

        self.init_x   = rospy.get_param("~init_x",   0.051)
        self.init_y   = rospy.get_param("~init_y",   0.001)
        self.init_yaw = rospy.get_param("~init_yaw", 0.008)

        self.cov_thresh = rospy.get_param("~cov_threshold", 1.5)
        self.spin_speed = rospy.get_param("~spin_speed",    0.5)
        self.max_wait   = rospy.get_param("~max_wait",      45.0)

        self.converged = False
        self.cmd_pub   = rospy.Publisher("/cmd_vel", Twist, queue_size=1)
        self.pose_pub  = rospy.Publisher("/initialpose",
                                         PoseWithCovarianceStamped, queue_size=1)
        rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, self._pose_cb)

    def _pose_cb(self, msg):
        cov = msg.pose.covariance
        uncertainty = math.sqrt(cov[0] ** 2 + cov[7] ** 2)
        rospy.loginfo_throttle(2, "[AutoLocalizer] Belirsizlik: %.4f (hedef < %.2f)",
                               uncertainty, self.cov_thresh)
        if uncertainty < self.cov_thresh:
            self.converged = True

    def _publish_initial_pose(self):
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = "map"
        msg.header.stamp    = rospy.Time.now()
        msg.pose.pose.position.x    = self.init_x
        msg.pose.pose.position.y    = self.init_y
        msg.pose.pose.position.z    = 0.0
        msg.pose.pose.orientation   = yaw_to_quat(self.init_yaw)
        # Orta büyüklükte kovaryans: konuma güveniyoruz ama Gazebo'da
        # her başlatmada küçük farklar olabilir
        c = [0.0] * 36
        c[0]  = 0.25   # x varyansı
        c[7]  = 0.25   # y varyansı
        c[35] = 0.07   # yaw varyansı
        msg.pose.covariance = c
        self.pose_pub.publish(msg)

    def _stop(self):
        self.cmd_pub.publish(Twist())
        rospy.sleep(0.3)

    def run(self):
        
        rospy.loginfo("[AutoLocalizer] AMCL bekleniyor...")
        rospy.sleep(2.0)

        rospy.loginfo("[AutoLocalizer] Başlangıç konumu gönderiliyor (%.3f, %.3f, yaw=%.3f)",
                      self.init_x, self.init_y, self.init_yaw)
        for _ in range(3):
            self._publish_initial_pose()
            rospy.sleep(0.3)

        rospy.sleep(0.5)
        rospy.loginfo("[AutoLocalizer] Kısa spin ile ince ayar yapılıyor...")

        twist = Twist()
        twist.angular.z = self.spin_speed
        rate      = rospy.Rate(10)
        start     = rospy.Time.now()
        min_spin  = rospy.Duration(3.0)

        while not rospy.is_shutdown():
            elapsed = rospy.Time.now() - start

            if elapsed > rospy.Duration(self.max_wait):
                rospy.logwarn("[AutoLocalizer] Zaman aşımı — devam ediliyor.")
                break

            if self.converged and elapsed > min_spin:
                rospy.loginfo("[AutoLocalizer] Konum doğrulandı!")
                break

            self.cmd_pub.publish(twist)
            rate.sleep()

        self._stop()
        rospy.loginfo("[AutoLocalizer] Tamamlandı.")


if __name__ == "__main__":
    try:
        AutoLocalizer().run()
    except rospy.ROSInterruptException:
        pass
