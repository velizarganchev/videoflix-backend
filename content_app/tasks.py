import subprocess


def convert_to_120p(video_path):
    # Convert the video to 120p
    target = video_path.replace('.mp4', '_120p.mp4')
    cmd = f'ffmpeg -i {video_path} -vf scale=854:120 {target} -y'
    try:
        subprocess.run(cmd, shell=True, check=True)
        return target
    except subprocess.CalledProcessError as e:
        print(f"Error converting to 120p: {e}")
        return None


def convert_to_360p(video_path):
    # Convert the video to 360p
    target = video_path.replace('.mp4', '_360p.mp4')
    cmd = f'ffmpeg -i {video_path} -vf scale=640:360 {target} -y'
    try:
        subprocess.run(cmd, shell=True, check=True)
        return target
    except subprocess.CalledProcessError as e:
        print(f"Error converting to 360p: {e}")
        return None


def convert_to_720p(video_path):
    # Convert the video to 720p
    target = video_path.replace('.mp4', '_720p.mp4')
    cmd = f'ffmpeg -i {video_path} -vf scale=1280:720 {target} -y'
    try:
        subprocess.run(cmd, shell=True, check=True)
        return target
    except subprocess.CalledProcessError as e:
        print(f"Error converting to 720p: {e}")
        return None


def convert_to_1080p(video_path):
    # Convert the video to 1080p
    target = video_path.replace('.mp4', '_1080p.mp4')
    cmd = f'ffmpeg -i {video_path} -vf scale=1920:1080 {target} -y'
    try:
        subprocess.run(cmd, shell=True, check=True)
        return target
    except subprocess.CalledProcessError as e:
        print(f"Error converting to 1080p: {e}")
        return None
