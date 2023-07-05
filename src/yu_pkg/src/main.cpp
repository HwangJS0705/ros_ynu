#include <ros/ros.h>
#include <sensor_msgs/LaserScan.h>
#include <std_msgs/String.h>
#include <geometry_msgs/Twist.h>
#include <string.h>
#include <iostream>
#define RAD2DEG(x) ((x)*180./M_PI)

using namespace std;


class PubandSub{
    private:
        ros::NodeHandle nh;
        ros::Subscriber sub_scan;
        ros::Subscriber sub_cam;
        ros::Publisher pub;
        geometry_msgs::Twist pubmsg;
    
    public:
        PubandSub(){
            sub_scan = nh.subscribe<sensor_msgs::LaserScan>("/scan", 1, &PubandSub::process_lidar,this);
        }

        void process_lidar(const sensor_msgs::LaserScan::ConstPtr& scan){
            int noise_error = 0;
            int count = (int)( 360. / RAD2DEG(scan->angle_increment));
            for(int i = 0; i < count; i++)
            {
                int degree = RAD2DEG(scan->angle_min + scan->angle_increment * i);
                float distance = scan->ranges[i];
                if((degree <= 45) && (degree >= -45) && (distance != 0.0))
                {
                    if(distance < 0.5)
                    {
                        noise_error++;
                    }
                }
            }
            if(noise_error >= 10)
            {
                ROS_INFO("Lidar Obstacle Detected !!");
                noise_error = 0;
            }
        }
};

int main(int argc, char **argv)
{
    ros::init(argc, argv, "teleop");
    PubandSub PaS;
    ros::spin();
    return 0;
}