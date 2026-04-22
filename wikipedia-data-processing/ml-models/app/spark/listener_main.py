import os
import sys

# When this file is executed directly via spark-submit using an absolute path,
# Python sets sys.path[0] to /app/spark. Add /app so package imports resolve.
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from spark.listener_runner import listen_and_retrain


if __name__ == "__main__":
    listen_and_retrain()
