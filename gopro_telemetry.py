import dateutil.parser
import subprocess
import shutil
import errno
import yaml
import json
import re
import os

class GoProTelemetry(object):

  def __init__(self, video_path, reprocess=False, prepend_filename_with_serial=False, config_path='config.yml'):
    GoProTelemetry.ensure_valid_path(video_path)
    self.ffprobe_streams = GoProTelemetry.get_ffprobe_streams(video_path)
    GoProTelemetry.ensure_valid_gopro_video(video_path, self.ffprobe_streams)

    self.gopro2gpx_path = None
    self.gopro2json_path = None
    self.gpmdinfo_path = None
    self.load_executables(config_path)
    # Instantiate attributes
    self.video_dir = os.path.abspath(os.path.join(video_path, os.pardir))
    self.filename = os.path.basename(video_path)
    self.basename = self.get_basename()
    self.video_path = os.path.abspath(video_path)
    self.telemetry_path = '{}.bin'.format(video_path)

    if prepend_filename_with_serial:
      self.process_prepend_filename_with_serial()

    self.extract_telemetry(reprocess)

  def get_basename(self):
    name_check = os.path.splitext(self.filename)[0]
    if not name_check.count('_'):
      return name_check
    elif name_check.count('_') == 1:
      return name_check.split('_')[1]
    else:
      raise Exception('Unknown filename format!')

  def process_prepend_filename_with_serial(self):
    self.camera_serial = self.get_camera_serial()
    if self.camera_serial not in self.filename:
      # Derive new filename and relevant paths
      new_filename = '{}_{}'.format(self.camera_serial, self.filename)
      new_video_path = self.video_path.replace(self.filename, new_filename)
      new_telemetry_path = self.telemetry_path.replace(self.filename, new_filename)

      # Update with new values
      self.filename = new_filename
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
      stream_index = self.get_stream_index('gpmd')
      command = GoProTelemetry.ffmpeg_command(self.video_path, stream_index, self.telemetry_path)
      GoProTelemetry.call_subprocess(command)

  def extract_all(self, reprocess=False):
    self.extract_gpx(reprocess)
    self.extract_json(reprocess)
    self.extract_metadata(reprocess)

  def extract_gpx(self, reprocess=False):
    gpx_path = os.path.join(self.video_dir, self.filename + '.gpx')
    # If reprocessing or gpx file does not yet exists
    if reprocess or not os.path.isfile(gpx_path):
      command = [
        self.gopro2gpx_path,
        '-i', self.telemetry_path,
        '-o', gpx_path
      ]
      GoProTelemetry.call_subprocess(command)

  def extract_json(self, reprocess=False):
    json_path = os.path.join(self.video_dir, self.filename + '.json')
    # If reprocessing or json file does not yet exists
    if reprocess or not os.path.isfile(json_path):
      command = [
        self.gopro2json_path,
        '-i', self.telemetry_path,
        '-o', json_path
      ]
      GoProTelemetry.call_subprocess(command)

  def extract_metadata(self, reprocess=False):
    gps_path = os.path.join(self.video_dir, self.filename + '_gps.csv')
    gyro_path = os.path.join(self.video_dir, self.filename + '_gyro.csv')
    accl_path = os.path.join(self.video_dir, self.filename + '_accl.csv')
    temp_path = os.path.join(self.video_dir, self.filename + '_temp.csv')
    
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

  def get_creation_time(self):
    timestamp = self.ffprobe_streams['format']['tags']['creation_time']
    return dateutil.parser.parse(timestamp)

  def get_firmware_version(self):
    return self.ffprobe_streams['format']['tags']['firmware']

  def get_camera_serial(self):
    stream_index = self.get_stream_index('fdsc')
    temp_output_path = '{}_fdsc.bin'.format(self.video_path)
    command = GoProTelemetry.ffmpeg_command(self.video_path, stream_index, temp_output_path)
    GoProTelemetry.call_subprocess(command)
    with open(temp_output_path, 'rb') as f:
      f.read(87)
      camera_serial = f.read(14).decode("utf-8")
    os.remove(temp_output_path) # delete temp file
    return camera_serial

  def get_stream_index(self, code_tag_string):
    for stream in self.ffprobe_streams['streams']:
      if stream['codec_tag_string'] == code_tag_string:
        return stream['index']

  @staticmethod
  def ensure_valid_path(file_path):
    if not os.path.isfile(file_path):
      raise OSError('{} is not a file!'.format(file_path))

  @staticmethod
  def get_ffprobe_streams(video_path):
    command = ['ffprobe', '-i', video_path, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', '-hide_banner']
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if err:
      print(err)
      return None
    return json.loads(out.decode('utf-8'))

  @staticmethod
  def ensure_valid_gopro_video(video_path, ffprobe_streams):
    found_gopro_indicator = False
    for stream in ffprobe_streams['streams']:
      if 'GoPro' in stream['tags']['handler_name']:
        found_gopro_indicator = True
        break
    if not found_gopro_indicator:
      raise Exception('{} is not a GoPro video!'.format(video_path))

  @staticmethod
  def ffmpeg_command(video_path, stream_index, output_path):
    return [
      'ffmpeg', '-v', 'quiet', '-y', '-i', video_path, '-codec', 'copy', '-map',
      '0:' + str(stream_index), '-f', 'rawvideo',
      output_path
    ]

  @staticmethod
  def call_subprocess(command):
    c = subprocess.run(command)
    if c.returncode != 0:
      raise subprocess.CalledProcessError(c.returncode, ' '.join(command))
