#!/usr/bin/env python
import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped, Pose
from styx_msgs.msg import TrafficLightArray, TrafficLight
from styx_msgs.msg import Lane
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from light_classification.tl_classifier import TLClassifier
import tf
import cv2
import yaml

STATE_COUNT_THRESHOLD = 3


class TLDetector(object):
    def __init__(self):
        """

        Whats is here?

        Subscribes to:
        /base_waypoints: [] Complete list of waypoints for the course
        /current_pos: Our Vehicle location
        /image_color: image stream from the car camera. Used to determine color of upcoming traffic
        /vehicle/traffic_lights: (x, y, z) coordinate of the traffic light

        Publishes to:
        /traffic_waypoints: returns the idx of the waypoint for nearest red light stop line.

        """
        rospy.init_node("tl_detector")

        self.pose = None
        self.waypoints = None
        self.camera_image = None
        self.lights = []

        sub1 = rospy.Subscriber("/current_pose", PoseStamped, self.pose_cb)
        sub2 = rospy.Subscriber("/base_waypoints", Lane, self.waypoints_cb)

        """
        /vehicle/traffic_lights provides you with the location of the traffic light in 3D map space and
        helps you acquire an accurate ground truth data source for the traffic light
        classifier by sending the current color state of all traffic lights in the
        simulator. When testing on the vehicle, the color state will not be available. You'll need to
        rely on the position of the light and the camera image to predict it.
        """
        sub3 = rospy.Subscriber(
            "/vehicle/traffic_lights", TrafficLightArray, self.traffic_cb
        )
        sub6 = rospy.Subscriber("/image_color", Image, self.image_cb)

        config_string = rospy.get_param("/traffic_light_config")
        self.config = yaml.load(config_string)

        self.upcoming_red_light_pub = rospy.Publisher(
            "/traffic_waypoint", Int32, queue_size=1
        )

        # --------------------------------------------------------------------------------
        # Set up the Classifier
        # --------------------------------------------------------------------------------
        self.bridge = CvBridge()
        self.light_classifier = TLClassifier()
        self.listener = tf.TransformListener()

        self.state = TrafficLight.UNKNOWN
        self.last_state = TrafficLight.UNKNOWN
        self.last_wp = -1
        self.state_count = 0

        rospy.spin()

    def pose_cb(self, msg):
        self.pose = msg

    def waypoints_cb(self, waypoints):
        self.waypoints = waypoints

    def traffic_cb(self, msg):
        self.lights = msg.lights

    def image_cb(self, msg):
        """Identifies red lights in the incoming camera image and publishes the index
            of the waypoint closest to the red light's stop line to /traffic_waypoint

        Args:
            msg (Image): image from car-mounted camera

        """
        self.has_image = True
        self.camera_image = msg
        light_wp, state = self.process_traffic_lights()

        """
        Publish upcoming red lights at camera frequency.
        Each predicted state has to occur `STATE_COUNT_THRESHOLD` number
        of times till we start using it. Otherwise the previous stable state is
        used.
        """

        # Handle cases where our classifier is noisy and output different light every frame.
        # With noisy classifiers we set self.state_count = 0. If the light state is consistent for say
        # STATE_COUNT_THRESHOLD frames we publish the light state
        if self.state != state:
            self.state_count = 0
            self.state = state
        elif self.state_count >= STATE_COUNT_THRESHOLD:
            self.last_state = self.state
            light_wp = light_wp if state == TrafficLight.RED else -1
            self.last_wp = light_wp
            self.upcoming_red_light_pub.publish(Int32(light_wp))
        else:
            self.upcoming_red_light_pub.publish(Int32(self.last_wp))
        self.state_count += 1

    def get_closest_waypoint(self, x, y):
        """Identifies the closest path waypoint to the given position
            https://en.wikipedia.org/wiki/Closest_pair_of_points_problem
        Args:
            pose (Pose): position to match a waypoint to

        Returns:
            int: index of the closest waypoint in self.waypoints

        """
        closest_idx = self.waypoints.tree.query([x, y], 1)[1]
        return closest_idx

    def get_light_state(self, light):
        """Determines the current color of the traffic light

        Args:
            light (TrafficLight): light to classify

        Returns:
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        # if not self.has_image:
        #     self.prev_light_loc = None
        #     return False
        #
        # cv_image = self.bridge.imgmsg_to_cv2(self.camera_image, "bgr8")
        #
        # # Get classification
        # # return self.light_classifier.get_classification(cv_image)

        # TODO: Implement logic to call the classifier to get the light color
        return light.state

    def process_traffic_lights(self):
        """Finds closest visible traffic light, if one exists, and determines its
            location and color

        Returns:
            int: index of waypoint closes to the upcoming stop line for a traffic light (-1 if none exists)
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        Whats in here?
        closest_light: The closest traffic light our current position
        line_wp_idx: Each traffic light come with a traffic line (the line where we need our car to stop). We should infact
                     fetch the idx for the closest traffic line. So we know where to stop

        # TODO: Log the values of closest_traffic_line, closest_traffic_light_waypoint if they withing a buffer distance to our car position. (Helpfull debugging functionality while adding the classifiaction part)
        """
        closest_light = None
        line_wp_idx = None

        # List of positions that correspond to the line to stop in front of for a given intersection
        stop_line_positions = self.config["stop_line_positions"]
        if self.pose:
            # Get the closest waypoint idx based on out car position
            car_wp_idx = self.get_closest_waypoint(
                self.pose.pose.position.x, self.pose.pose.position.y
            )

            diff = len(self.waypoints.waypoints)
            for i, light in enumerate(self.lights):
                line = stop_line_positions[i]
                # Get the closest waypoint based on the traffic line, where we might want to stop
                temp_wp_idx = self.get_closest_waypoint(line[0], line[1])
                d = temp_wp_idx - car_wp_idx
                if d >= 0 and d < diff:
                    diff = d
                    closest_light = light
                    line_wp_idx = temp_wp_idx

        if closest_light:
            # TODO find the closest visible traffic light (if one exists)
            state = self.get_light_state(closest_light)
            return line_wp_idx, state

        self.waypoints = None
        return -1, TrafficLight.UNKNOWN


if __name__ == "__main__":
    try:
        TLDetector()
    except rospy.ROSInterruptException:
        rospy.logerr("Could not start traffic node.")
