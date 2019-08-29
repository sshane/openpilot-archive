import ftplib
import json
import string
import random
import os
from selfdrive.op_params import opParams
op_params = opParams()

def upload_data():
  filepath = "/data/openpilot/selfdrive/data_collection/df-data"
  if os.path.isfile(filepath):
    if op_params.get("uniqueID") is None:
      op_params.put("uniqueID", ''.join([random.choice(string.lowercase + string.uppercase + string.digits) for i in range(15)]))
    try:
      username = op_params.get("uniqueID", ''.join([random.choice(string.lowercase + string.uppercase + string.digits) for i in range(15)]))
      try:
        with open("/data/data/ai.comma.plus.offroad/files/persistStore/persist-auth", "r") as f:
          auth = json.loads(f.read())
        auth = json.loads(auth['commaUser'])
        if str(auth['username']) != "":
          username = str(auth['username'])
      except:
        pass

      car = op_params.get("cachedFingerprint")
      if car is not None:
        username += "-{}".format(car[0])

      df_num = op_params.get('df_num', default=0)  # number of files uploaded
      filename = "df-data.{}".format(df_num)

      ftp = ftplib.FTP("smiskol.com")
      ftp.login("dfv2", "TK2f4cM@mpVY>um~")
      with open(filepath, "rb") as f:
        try:
          ftp.mkd("/{}".format(username))
        except:
          pass
        ftp.storbinary("STOR /{}/{}".format(username, filename), f)
      ftp.quit()
      os.remove(filepath)
      op_params.put('df_num', df_num + 1)  # increment number of files uploaded so we don't overwrite existing files on server
      return True
    except:
      return False
  else:
    return False