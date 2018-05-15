#!/usr/bin/python3.5
# -*- coding: utf-8 -*-

import subprocess
import os.path
import shutil
import errno
import yaml

class GoProTelemetry(object):

  def __init__(self, video_path, reprocess=False, config_path='./config.yml'):
    if os.path.isfile(video_path) and video_path.endswith('.MP4'):
      self.gopro2gpx_path = None
      self.gopro2json_path = None
      self.gpmdinfo_path = None
      self.load_executables(config_path)
      # Instantiate attributes
      self.video_path = os.path.abspath(video_path)
      self.video_dir = os.path.abspath(os.path.join(video_path, os.pardir))
      self.telemetry_path = video_path + '.bin'
      self.base_name = os.path.basename(video_path)

      self.extract_telemetry(reprocess)
    else:
      raise Exception('No MP4 file at ' + video_path)

  def load_executables(self, config_path):
    with open(config_path, 'r') as cfg:
      gopro_lib = yaml.load(cfg)['gopro']
    self.gopro2gpx_path = os.path.expanduser(gopro_lib['to_gpx'])
    self.gopro2json_path = os.path.expanduser(gopro_lib['to_json'])
    self.gpmdinfo_path =  os.path.expanduser(gopro_lib['gpmd_info'])

  def extract_telemetry(self, reprocess=False):
    # If reprocessing or telemetry binary does not yet exists
    if reprocess or not os.path.isfile(self.telemetry_path):
      GoProTelemetry.call_subprocess(self.telemetry_command())

  def extract_all(self, reprocess=False):
    self.extract_gpx(reprocess)
    self.extract_json(reprocess)
    self.extract_metadata(reprocess)

  def extract_gpx(self, reprocess=False):
    gpx_path = os.path.join(self.video_dir, self.base_name + '.gpx')
    # If reprocessing or gpx file does not yet exists
    if reprocess or not os.path.isfile(gpx_path):
      command = [
        self.gopro2gpx_path,
        '-i', self.telemetry_path,
        '-o', gpx_path
      ]
      GoProTelemetry.call_subprocess(command)

  def extract_json(self, reprocess=False):
    json_path = os.path.join(self.video_dir, self.base_name + '.json')
    # If reprocessing or json file does not yet exists
    if reprocess or not os.path.isfile(json_path):
      command = [
        self.gopro2json_path,
        '-i', self.telemetry_path,
        '-o', json_path
      ]
      GoProTelemetry.call_subprocess(command)

  def extract_metadata(self, reprocess=False):
    gps_path = os.path.join(self.video_dir, self.base_name + '_gps.csv')
    gyro_path = os.path.join(self.video_dir, self.base_name + '_gyro.csv')
    accl_path = os.path.join(self.video_dir, self.base_name + '_accl.csv')
    temp_path = os.path.join(self.video_dir, self.base_name + '_temp.csv')
    
    # If reprocessing or none of the metadata files yet exists
    if reprocess or not (
      os.path.isfile(gps_path) and
      os.path.isfile(gyro_path) and
      os.path.isfile(accl_path) and
      os.path.isfile(temp_path)):
      
      command = [
        self.gpmdinfo_path,
        '-i', self.telemetry_path
      ]
      GoProTelemetry.call_subprocess(command)
      
      # Rename and move files into video directory
      shutil.move('./gps.csv', gps_path)
      shutil.move('./gyro.csv', gyro_path)
      shutil.move('./accl.csv', accl_path)
      shutil.move('./temp.csv', temp_path)

  def telemetry_command(self, m='3'):
    return [
      'ffmpeg', '-y', '-i', self.video_path, '-codec', 'copy', '-map',
      '0:' + m + ':handler_name:" GoPro MET"', '-f', 'rawvideo',
      self.telemetry_path
    ]

  @staticmethod
  def call_subprocess(command):
    c = subprocess.run(command)
    if c.returncode != 0:
      raise subprocess.CalledProcessError(c.stderr)
