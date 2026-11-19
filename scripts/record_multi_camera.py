#!/usr/bin/env python3
"""Grava as duas câmeras anotadas lado a lado em um vídeo MP4."""

import os
import shutil
import subprocess
import threading

import cv2
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import Bool


class Recorder:
    """Sincroniza, combina e finaliza o vídeo das duas câmeras."""

    def __init__(self):
        self.bridge = CvBridge()
        self.writer = None
        self.closed = False
        self.lock = threading.RLock()
        self.left = None
        self.right = None
        self.path = rospy.get_param('~path')
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        rospy.Subscriber('/camera_1/annotated', Image, self.receive_left, queue_size=2)
        rospy.Subscriber('/camera_2/annotated', Image, self.receive_right, queue_size=2)
        rospy.Subscriber('/multi_camera/done', Bool, self.done)
        rospy.on_shutdown(self.close)

    def receive_left(self, message):
        self.receive(message, 'left')

    def receive_right(self, message):
        self.receive(message, 'right')

    def receive(self, message, side):
        with self.lock:
            if self.closed:
                return
            image = self.bridge.imgmsg_to_cv2(message, 'bgr8')
            if side == 'left':
                self.left = image
            else:
                self.right = image
            if self.left is None or self.right is None:
                return
            if self.writer is None:
                height = min(self.left.shape[0], self.right.shape[0])
                width = self.left.shape[1] + self.right.shape[1]
                self.writer = cv2.VideoWriter(
                    self.path, cv2.VideoWriter_fourcc(*'mp4v'), 15, (width, height),
                )
                if not self.writer.isOpened():
                    raise RuntimeError('Cannot open video output')
            frame = cv2.hconcat([self.left, self.right])
            cv2.putText(frame, 'camera_1 | camera_2 | t=%.2f s' % message.header.stamp.to_sec(),
                        (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            self.writer.write(frame)

    def done(self, message):
        if message.data:
            rospy.signal_shutdown('Patrol finished')

    def close(self):
        """Finaliza a gravação uma única vez."""
        with self.lock:
            if self.closed:
                return
            self.closed = True
            if self.writer is None:
                return
            self.writer.release()
            self.writer = None
            if shutil.which('ffmpeg'):
                converted = self.path + '.h264.mp4'
                result = subprocess.run([
                    'ffmpeg', '-y', '-loglevel', 'error', '-i', self.path,
                    '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', converted,
                ])
                if result.returncode == 0:
                    os.replace(converted, self.path)
                else:
                    rospy.logwarn('Falha na conversão H.264; vídeo original preservado')


if __name__ == '__main__':
    rospy.init_node('record_multi_camera')
    Recorder()
    rospy.spin()
