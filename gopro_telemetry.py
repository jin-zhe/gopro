import subprocess
import shutil
import errno
import yaml
import json
import re
import os

class GoProTelemetry(object):

  def __init__(self, video_path, reprocess=False, unique_naming=False, config_path='config.yml'):
    if os.path.isfile(video_path) and video_path.endswith('.MP4'):
      self.gopro2gpx_path = None
      self.gopro2json_path = None
      self.gpmdinfo_path = None
      self.load_executables(config_path)
      # Instantiate attributes
      self.base_name = os.path.basename(video_path)
      self.video_dir = os.path.abspath(os.path.join(video_path, os.pardir))
      self.video_path = os.path.abspath(video_path)
      self.telemetry_path = video_path + '.bin'

      if unique_naming:
        self.process_unique_naming()

      self.extract_telemetry(reprocess)
    else:
      raise Exception('No MP4 file at ' + video_path)

  def process_unique_naming(self):
    # Derive new basename and relevant paths
    self.camera_serial = self.get_camera_serial()
    new_base_name = '{}_{}'.format(self.camera_serial, self.base_name)
    new_video_path = self.video_path.replace(self.base_name, new_base_name)
    new_telemetry_path = self.telemetry_path.replace(self.base_name, new_base_name)

    # Update with new values
    self.base_name = new_base_name
    os.rename(self.video_path, new_video_path)
    self.video_path = new_video_path
    self.telemetry_path = new_telemetry_path

  def load_executables(self, config_path):
    config_path = os.path.join(os.path.dirname(__file__), config_path)
    with open(config_path, 'r') as cfg:
      gopro_lib = yaml.load(cfg)['gopro']
    self.gopro2gpx_path = os.path.expanduser(gopro_lib['to_gpx'])
    self.gopro2json_path = os.path.expanduser(gopro_lib['to_json'])
    self.gpmdinfo_path =  os.path.expanduser(gopro_lib['gpmd_info'])

  def extract_telemetry(self, reprocess=False):
    # If reprocessing or telemetry binary does not yet exists
    if reprocess or not os.path.isfile(self.telemetry_path):
      stream_index = GoProTelemetry.get_stream_index(self.video_path, 'gpmd')
      command = GoProTelemetry.ffmpeg_command(self.video_path, stream_index, self.telemetry_path)
      GoProTelemetry.call_subprocess(command)

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

  def get_camera_serial(self):
    stream_index = GoProTelemetry.get_stream_index(self.video_path, 'fdsc')
    temp_output_path = self.video_path + '_fdsc.bin'
    command = GoProTelemetry.ffmpeg_command(self.video_path, stream_index, temp_output_path)
    GoProTelemetry.call_subprocess(command)
    with open(temp_output_path, 'rb') as f:
      f.read(87)
      camera_serial = f.read(14).decode("utf-8")
    os.remove(temp_output_path) # delete temp file
    return camera_serial

  @staticmethod
  def ffmpeg_command(video_path, stream_index, output_path):
    return [
      'ffmpeg', '-v', 'quiet', '-y', '-i', video_path, '-codec', 'copy', '-map',
      '0:' + str(stream_index), '-f', 'rawvideo',
      output_path
    ]

  @staticmethod
  def get_stream_index(video_path, code_tag_string):
    command = ['ffprobe', '-i', video_path, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', '-hide_banner']
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if err:
      print(err)
      return None
    gopro_streams = json.loads(out.decode('utf-8'))['streams']
    for stream in gopro_streams:
      if stream['codec_tag_string'] == code_tag_string:
        return stream['index']

  @staticmethod
  def call_subprocess(command):
    c = subprocess.run(command)
    if c.returncode != 0:
      raise subprocess.CalledProcessError(c.returncode, ' '.join(command))
