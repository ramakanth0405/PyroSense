import os

from config import load_config
from dashboard import Dashboard
from monitor import Monitor


def main():
    config = load_config()
    tls_option = "tls_verify;0|" if config["insecure_tls"] else ""
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = tls_option + "rtsp_transport;tcp"
    monitor = Monitor(config)
    Dashboard(monitor, config["dashboard_port"]).start()
    monitor.run()


if __name__ == "__main__":
    main()
