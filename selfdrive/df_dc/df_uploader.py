import ftplib
import json
import string
import random
import os
from common.op_params import opParams
op_params = opParams()


def generate_random_username():
  return ''.join([random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for i in range(15)])


def upload_data():
  base_dir = "/data/openpilot/selfdrive/df_dc/"
  file_names = ["df-data", "brake-data"]

  for file_name in file_names:
    print(file_name)
    file_path = os.path.join(base_dir, file_name)
    print(file_path)
    if os.path.isfile(file_path) and os.path.getsize(file_path) > 2*10**6:  # ensure the file is at least 2 mb
      file_name += '.{}'
      print(file_name)
      username = op_params.get("uniqueID", None)
      if username is None:
        op_params.put("uniqueID", generate_random_username())
        username = op_params.get("uniqueID", "u-error")
      username += "-{}".format(op_params.get("car_model", 'unknown-car'))
      print(username)
      try:
        new_folder = False
        ftp = ftplib.FTP("smiskol.com")
        ftp.login("dfv2", "TK2f4cM@mpVY>um~")
        if username not in ftp.nlst():
          ftp.mkd("/{}".format(username))
          new_folder = True
        ftp.cwd("/{}".format(username))
        print(new_folder)
        if not new_folder:
          data_files = ftp.nlst()
          files = []
          for i in data_files:
            try:
              if 'txt' not in i and '.' in i and file_name[:-3] in i:
                ftp.size(i)  # filters out folders
                files.append(i)
            except:
              pass
          file_num = max([int(i.split('.')[1]) for i in files]) + 1
        else:
          file_num = 0
        print(file_num)
        uploaded = False
        tries = 0

        with open(file_path, "rb") as f:
          while tries <= 5:
            try:
              result = ftp.storbinary("STOR {}".format(file_name.format(file_num)), f)
              if '226' in result:
                uploaded = True
                break
            except:
              pass
            tries += 1
        ftp.quit()
        if uploaded:
          os.remove(file_path)
      except Exception as e:
        print(e)
    else:
      print('{} does not exist or is too small'.format(file_path))


upload_data()