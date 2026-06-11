#!/usr/bin/env python3
"""
GCS'den gelen /gcs/save_map mesajını alınca map_saver çalıştırır
ve sonucu /gcs/save_map_result topic'ine yazar.
"""
import os
import subprocess
import rospy
from std_msgs.msg import String

MAP_PATH = os.path.expanduser(
    "~/service_robot/src/service_robot_mission/maps/map"
)

def on_save_request(msg):
    rospy.loginfo("[MapSaver] Harita kaydediliyor: %s", MAP_PATH)
    result_pub = rospy.Publisher("/gcs/save_map_result", String, queue_size=1)
    rospy.sleep(0.2)  # publisher register

    try:
        ret = subprocess.run(
            ["rosrun", "map_server", "map_saver", "-f", MAP_PATH],
            timeout=15,
            capture_output=True,
            text=True
        )
        if ret.returncode == 0:
            rospy.loginfo("[MapSaver] Başarıyla kaydedildi.")
            result_pub.publish(String(data="ok"))
        else:
            rospy.logerr("[MapSaver] Hata: %s", ret.stderr)
            result_pub.publish(String(data="error:" + ret.stderr[:120]))
    except subprocess.TimeoutExpired:
        rospy.logerr("[MapSaver] Zaman aşımı.")
        result_pub.publish(String(data="error:timeout"))
    except Exception as e:
        rospy.logerr("[MapSaver] %s", str(e))
        result_pub.publish(String(data="error:" + str(e)[:120]))


if __name__ == "__main__":
    rospy.init_node("map_saver_node", anonymous=False)
    rospy.Subscriber("/gcs/save_map", String, on_save_request, queue_size=1)
    rospy.loginfo("[MapSaver] Hazır — /gcs/save_map bekleniyor.")
    rospy.spin()
