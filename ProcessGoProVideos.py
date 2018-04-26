#!/usr/bin/python3.5
# -*- coding: utf-8 -*-

import tqdm
import sys
import os
from GoProTelemetry import GoProTelemetry

def main(video_dir):
  video_dir = os.path.abspath(video_dir)
  GoPro_videos = list(filter(lambda f: f.endswith('.MP4'), os.listdir(video_dir)))
  for filename in tqdm.tqdm(GoPro_videos, total=len(GoPro_videos), desc='Processing ' + video_dir):
    file_path = os.path.abspath(os.path.join(video_dir, filename))
    gopro_telemetry = GoProTelemetry(file_path)
    gopro_telemetry.extract_all(False)

if __name__ == '__main__':
  main(sys.argv[1])
