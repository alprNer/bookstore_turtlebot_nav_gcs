#!/usr/bin/env python3
"""
QR Kod Okuyucu Node
/camera/rgb/image_raw topic'inden görüntü alır, pyzbar ile QR kodlarını çözer,
sonucu /qr_code/data topic'ine (std_msgs/String) yayınlar.
"""
import rospy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
from pyzbar import pyzbar


class QRReaderNode:
    def __init__(self):
        rospy.init_node("qr_reader", anonymous=False)

        self.bridge = CvBridge()
        self.pub = rospy.Publisher("/qr_code/data", String, queue_size=10)
        self.sub = rospy.Subscriber(
            "/camera/rgb/image_raw", Image, self._image_cb, queue_size=1,
            buff_size=2**24
        )
        rospy.loginfo("[QRReader] Hazır — /camera/rgb/image_raw dinleniyor.")

    def _image_cb(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            rospy.logerr(f"[QRReader] cv_bridge hatası: {e}")
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        for obj in pyzbar.decode(gray):
            data = obj.data.decode("utf-8").strip()
            rospy.loginfo(f"[QRReader] Okundu: '{data}'")
            self.pub.publish(String(data=data))

    def run(self):
        rospy.spin()


if __name__ == "__main__":
    QRReaderNode().run()
