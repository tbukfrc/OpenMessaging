import socketio
import pickle
import asyncio
import uvicorn
import datetime
import os
import bleach
import uuid
import base64
import json
from PIL import Image
from profanity_check import predict_prob
import marko
import pyotp
import qrcode
import redis
import bcrypt

with open('config.json', 'r') as config:
  data = json.loads(config.read())
  ADMIN_LIST = data['admins']
  REDIS_PORT = data['redis_port']
  SERVER_PORT = data['server_port']
  ADMIN_UPLOAD_LIMIT = data['admin_upload_limit']
  USER_UPLOAD_LIMIT = data['user_upload_limit']
  MESSAGE_CHARACTER_LIMIT = data['character_limit']
  CDN_DOMAIN = data['cdn_domain']

r = redis.Redis(host='localhost', port=REDIS_PORT, db=0)
def save(data, location: str) -> None:
  r.set(location, json.dumps(data))

def load(location: str):
  if r.get(location) == None:
    r.set(location, json.dumps({}))
    return json.loads(r.get(location))
  else:
    return json.loads(r.get(location))

def load_room(room: str):
  room = load(load('rooms')[room])
  return room

if r.get('userIndex') == None:
  save({}, 'userIndex')
if r.get('rooms') == None:
  save({'main': 'roommain'}, 'rooms')
if r.get('roommain') == None:
  save({'owner': '[SYSTEM]', 'protected': False, 'password': None, 'messages': []}, 'roommain')
if r.get('banned') == None:
  save({}, 'banned')

# Code newly refactored and commented on 1/10/2023

# Don't change this variable, it's just a default value. The current version will be automatically
# determined by the latest changelog filename.
updateVer = '0.0.0.0'
# This list is used to store temporary keys to identify a user when changing their password (2FA)
temp_pass_keys = []
# This list is used in ratelimiting to store the # of messages a user has sent recently
global sid_ratelimit
sid_ratelimit = []

active_upload_keys = {}

# iterate through the chnglog- files and determine the latest one based on version number
changelogs = []
for file in os.listdir():
  if file.startswith('chnglog'):
    changelogs.append(file)
    if int(file.replace('.', '').split('-')[1]) > int(updateVer.replace('.', '')):
      updateVer = file.split('-')[1]

# opens the latest changelog and saves it in memory.
if changelogs:
  with open('chnglog-' + updateVer, 'r') as changes:
    changelog = changes.read()
  changes.close()

# create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# wrap with a ASGI application.
app = socketio.ASGIApp(sio)

# initialize required variables
# validSids keeps track of logged-in users
# alphanumeric_list is for checking if inputs contain alphanumeric characters
global messages
validSids = {}
secretStore = {}
alphanumeric_list = list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_-')

try:
  with open('secret.store', 'rb') as secretStoreLoad:
    secretStore = pickle.load(secretStoreLoad)
except(FileNotFoundError):
  print('secret.store does not exist')

# This is a client endpoint that requests an UploadKey, which is a
# uuid4 key that is used on the server-side to seperate file uploads
# when files are being asynchronously uploaded in chunks
@sio.event
async def requestUploadKey(sid):
  # For future reference, every time you see this, it is checking if the user's SID#
  # is a registered SID
  check = await validate_sid(sid)
  if not check:
    return
  upload_key = str(uuid.uuid4())
  active_upload_keys[upload_key] = ''
  await sio.emit('uploadKeyCallback', upload_key, room=sid)

# This is the code that handles async data uploads via
# UploadKeys. If you ever have to work on this code, I'm sorry.
# This code is a complete mess, but I couldn't come up with a better solution.
# Unless you're adding custom datatypes, however, you probably won't have to deal with this.
@sio.event
async def dataSend(sid, data):
  room = await sio.get_session(sid)
  username = await validate_sid(sid)
  if not username:
    return
  if data['id'] in active_upload_keys:
    if data['part'] == 'transferComplete':
      mime = active_upload_keys[data['id']].split(',')[0]
      print(mime)
      if 'video' in mime:
        active_upload_keys[data['id']] = active_upload_keys[data['id']].split(',')[1]
        filepath = f'/home/mainsrv/Documents/OpenMessaging/cdn/{room["room"]}/{data["id"]}'
        os.makedirs(filepath)
        with open(f'{filepath}/vid.mp4', 'wb') as video:
          video.write(base64.b64decode(active_upload_keys[data['id']]))
        video.close()
        active_upload_keys[data['id']] = 'video controls!&vid.mp4'
      elif 'image' in mime:
        active_upload_keys[data['id']] = active_upload_keys[data['id']].split(',')[1]
        filepath = f'/home/mainsrv/Documents/OpenMessaging/cdn/{room["room"]}/{data["id"]}'
        os.makedirs(filepath)
        with open(f'{filepath}/img.png', 'wb') as image:
          image.write(base64.b64decode(active_upload_keys[data['id']]))
        image.close()
        pre = Image.open(f'{filepath}/img.png')
        pre.thumbnail((500,500), Image.LANCZOS)
        pre.save(f'{filepath}/thumbnail.png', optimize=True, quality=80)
        active_upload_keys[data['id']] = 'img!&thumbnail.png'
      elif 'omtheme' in mime:
        rdata = json.loads(active_upload_keys[data['id']])
        raw = active_upload_keys[data['id']]
        active_upload_keys[data['id']] = f'omtheme!&{rdata["name"]}.omtheme!&{raw}'
        del raw
        del rdata
      elif 'omext' in mime:
        rdata = json.loads(active_upload_keys[data['id']])
        raw = active_upload_keys[data['id']]
        active_upload_keys[data['id']] = f'omext!&{rdata["name"]}.omext!&{raw}'
        del raw
        del rdata
    else:  
      active_upload_keys[data['id']] += data['part']
      size = (len(active_upload_keys[data['id']]) * (3/4)) - 2
      if username in ADMIN_LIST:
        if size/1000000 > ADMIN_UPLOAD_LIMIT:
          await sio.emit('statusCallback', {'error': 'fileTooLarge', 'description': 'Maximum file size is 100MB.'}, room=sid)
          active_upload_keys[data['id']] = ''
          return
      elif size/1000000 > USER_UPLOAD_LIMIT:
        await sio.emit('statusCallback', {'error': 'fileTooLarge', 'description': 'Maximum file size is 50MB.'}, room=sid)
        active_upload_keys[data['id']] = ''
        return

# This code sends the new room data to all the clients. It's pretty self-explanitory.
async def sendNewRooms(): 
  rooms = []
  for room in load('rooms'):
    rooms.append({'name': room, 'protected': load_room(room)['protected']})
  await sio.emit('recieveRooms', rooms)

# This code initializes a client. It sets up their sid# in the ratelimiter,
# enter's them into the main room, and sends the room info to them.
@sio.event
async def connect(sid, environ, auth):
  global sid_ratelimit
  sid_ratelimit.append({'sid': sid, 'msgs': 0})
  sio.enter_room(sid, 'main')
  await sio.save_session(sid, {'room': 'main'})
  await sendNewRooms()
  #await sio.emit('statusCallback', {'error': 'Canary Build', 'description': 'This is the canary/testing version of OpenMessage. New features are actively developed and tested here. There may be severe bugs.'}, room=sid)

# This code is some async code that lowers the current sent messages
# by one every two seconds. You can modify the sleep time to increase or decrease
# the strictness of the ratelimiter.
async def ratelimiter():
  while True:
    for sid in sid_ratelimit:
      if sid['msgs'] != 0:
        sid['msgs'] -= 1
    await asyncio.sleep(2)

# This just removes a users SID# from the valid SID#s when they disconnect.
@sio.event
def disconnect(sid):
  if sid in validSids:
    del validSids[sid]

# This function warns people who are using Safari iOS, because OpenMessage doesn't fully work on Safari iOS.
@sio.event
async def browserSafari(sid, safari):
  if safari:
    await sio.emit('statusCallback', {'error': 'Browser Error', 'description': 'This web app runs poorly on Safari. It is recommended to a Chromium-based browser, or Firefox.'}, room=sid)

# Client requests this endpoint to check if their client's last login was up to date.
# If it wasn't server sends back the latest changelong, and current version.
@sio.event
async def versionNum(sid, version):
  if version != updateVer:
    await sio.emit('statusCallback', {'changelog': updateVer, 'description': changelog}, room=sid)

# Client requests this endpoint to recieve message history for their current channel.
# Unfortunately, this currently returns the entire message history of the room, so long chats could break this.
# In the future, I plan to implement infinite-scrolling and loading.
@sio.event
async def requestUpdate(sid):
  room = await sio.get_session(sid)
  await getHistory(sid, room['room'])

async def validate_sid(sidNum):
  if sidNum in validSids:
    return validSids[sidNum]
  else:
    await sio.emit('statusCallback', {'error': 'failedToValidateSid', 'description': 'Failed to validate sid number with message author'}, room=sid)
    return False
  
async def transfer_room(sidNum, old, new):
  await getHistory(sidNum, new)
  await sendNewRooms()
  sio.leave_room(sidNum, old)
  sio.enter_room(sidNum, new)
  await sio.save_session(sidNum, {'room': new})

# This code is (generally) simple. It gets the room you're in, finds the message with the ID you gave, checks if
# you wrote the message, and edits it with the given content.
@sio.event
async def editMessage(sid, idNum, content):
  room = await sio.get_session(sid)
  username = await validate_sid(sid)
  if not username:
    return
  messages = load_room(room['room'])
  for message in messages['messages']:
    if message['id'] == idNum:
      if username == message['author']:
        indx = messages['messages'].index(message)
        messages['messages'][indx]['content'] = marko.convert(bleach.clean(content, tags=['p', 'b', 'i', 'a', 'u', 's']))
        save(messages, load('rooms')[room['room']])
        await getHistoryAll(room['room'])
      else:
        await sio.emit('statusCallback', {'error': 'notMessageAuthor', 'description': 'Only the message author can edit messages'}, room=sid)

# Same as the edit function, but this one deletes the message.
@sio.event
async def deleteMessage(sid, idNum):
  username = await validate_sid(sid)
  if not username:
    return
  room = await sio.get_session(sid)
  messages = load_room(room['room'])
  for message in messages['messages']:
    if message['id'] == idNum:
      if username == message['author'] or username in ADMIN_LIST:
        indx = messages['messages'].index(message)
        messages['messages'].pop(indx)
        save(messages, load('rooms')[room['room']])
        await getHistoryAll(room['room'])
      else:
        await sio.emit('statusCallback', {'error': 'notMessageAuthor', 'description': 'Only the message author can delete messages'}, room=sid)

# This function parses the given message before distributing it to other clients, and
# blocks messages that break rules. Add new commands lower down in this function.
@sio.event
async def recieve_msg(sid, data):
  print('message recieved. data: ' + str(data))
  message = data['msg']
  dataid = data['dataid']
  room = await sio.get_session(sid)
  global sid_ratelimit
  if sid in sid_ratelimit:
    if sid_ratelimit[sid]['msgs'] > 1:
      await sio.emit('statusCallback', {'error': 'tooManyMessages', 'description': 'You are being ratelimited.'}, room=sid)
      return
    else:
      sid_ratelimit[sid]['msgs'] += 1
  username = await validate_sid(sid)
  if not username:
    return
  if message == '':
    await sio.emit('statusCallback', {'error': 'emptyMessage', 'description': 'Messages may not be empty.'}, room=sid)
    return
  if username in load('banned'):
    await sio.emit('statusCallback', {'error': 'bannedUserError', 'description': 'Your account has been banned from participating in this chatroom.'}, room=sid)
    return
  if predict_prob([message]) > [0.9]:
    await sio.emit('statusCallback', {'error': 'profanityFilter', 'description': 'Your message had a profanity probability greater than the threshold of 90%. As such, your message has been deleted.'}, room=sid)
    return
  if len(message) > MESSAGE_CHARACTER_LIMIT:
    await sio.emit('statusCallback', {'error': 'messageLengthError', 'description': 'Maximum message length is 2000 characters'}, room=sid)
    return
  elif message.startswith('/clear') and username in ADMIN_LIST:
    messages = load_room(room['room'])
    messages['messages'] = []
    messages['messages'].append({'content': 'The chat has been cleared', 'author': '[SYSTEM]', 'color': 'system', 'id': load_room(room)['messages'][-1]['id'] + 1})
    save(messages, load('rooms')[room['room']])
    await getHistoryAll(room['room'])
  elif message.startswith('/ban') and username in ADMIN_LIST:
    reason = message.split('$+')[1]
    banned_user = message.split(' ')[1].split('$+')[0]
    messages = load_room(room['room'])
    for messaged in messages['messages']:
      if messaged['author'] == banned_user:
        indx = messages['messages'].index(messaged)
        messages['messages'][indx]['content'] = '[Removed]'
        messages['messages'][indx]['author'] = '[Banned User]'
    userStore = load('userIndex')
    if banned_user in userStore:
      banned_users = load('banned')
      banned_users[banned_user] = userStore[banned_user]
      del userStore[banned_user]
      save(banned_users, 'banned')
      save(userStore, 'userIndex')
    messages['messages'].append({'content': f'The user "{banned_user}" has been banned for the reason: {reason}.', 'author': '[SYSTEM]', 'color': 'system', 'id': load_room(room)['messages'][-1]['id'] + 1})
    save(messages, load('rooms')[room['room']])
    await getHistoryAll(room['room'])
  elif message.startswith('/popup') and username in ADMIN_LIST:
    await sio.emit('statusCallback', {'popup': "Admin Popup", 'description': message.replace('/popup ', '')})
    return
  elif message.startswith('/joinroom'):
    current_room = room['room']
    owned_rooms = 0
    parse = message.split(' ')
    room = parse[1]
    try:
      password = parse[2]
    except(IndexError):
      password = None
    if room not in load('rooms'):
      room_chars = list(room)
      for char in room_chars:
        if char not in alphanumeric_list:
          await sio.emit('statusCallback', {'error': 'alphanumericError', 'description': 'Room names can only contain alphanumeric characters, underscores (_), and dashes (-).'}, room=sid)
          return
      if len(room) > 30:
        await sio.emit('statusCallback', {'error': 'nameLengthError', 'description': 'Room names cannot be greater than 30 characters.'}, room=sid)
        return
      for rm in load('rooms'):
        if username == load_room(rm)['owner']:
          owned_rooms += 1
        if owned_rooms > 5 and username not in ADMIN_LIST:
            await sio.emit('statusCallback', {'error': 'Too many rooms', 'description': 'You own the maximum of 5 rooms already. You cannot create more rooms.'}, room=sid)
      room_id = str(uuid.uuid4())
      room_list = load('rooms')
      room_list[room] = room_id
      save(room_list, 'rooms')
      new_room = load(room_id)
      latest_id = 1
      new_room['messages'] = []
      new_room['messages'].append({'content': f'Room "{room}" created!', 'author': '[SYSTEM]', 'color': 'system', 'timestamp': str(datetime.datetime.now()), 'id': latest_id})
      new_room['owner'] = username
      new_room['protected'] = False
      new_room['password'] = None
      save(new_room, room_id)
      await transfer_room(sid, current_room, room)
      return
    elif load_room(room)['protected'] == True:
      if password == None:
        await sio.emit('statusCallback', {'error': 'protectedRoom', 'description': 'This room is protected. Please enter a password'}, room=sid)
        return
      elif load_room(room)['password'] == password:    
        await transfer_room(sid, current_room, room)
        return
      else:
        await sio.emit('statusCallback', {'error': 'incorrectPassword', 'description': 'You entered the incorrect password.'}, room=sid)
        return
    else:
      await transfer_room(sid, current_room, room)
      return
  elif message.startswith('/lock'):
    room_data = load_room(room['room'])
    if room_data['owner'] == username:
      lock = message.split(' ')
      password = lock[1]
      room_data['protected'] = True
      room_data['password'] = password
      save(room_data, load('rooms')[room['room']])
      await sendNewRooms()
      await sio.emit('statusCallback', {'popup': 'Room Secured', 'description': f'Room has been locked with the password: {password}. If this is incorrect, simply run the lock command again to change it.'}, room=sid)
      return
    else:
      await sio.emit('statusCallback', {'error': 'permissionError', 'description': 'You are not the owner of this room'}, room=sid)
  elif message.startswith('/delete'):
    if load_room(room['room'])['owner'] == username:
      rooms = message.split(' ')
      try:
        roomnm = rooms[1]
      except(IndexError):
        await sio.emit('statusCallback', {'error': 'invalidCommand', 'description': 'Type your name after the delete command to delete the channel. (Ex. /delete example)'}, room=sid)
      if roomnm == room['room']:
        del messages[roomnm]
        await transfer_room(sid, room['room'], 'main')
      else:
        await sio.emit('statusCallback', {'error': 'invalidCommand', 'description': 'Type your name after the delete command to delete the channel. (Ex. /delete example)'}, room=sid)
      return
    else:
      await sio.emit('statusCallback', {'error': 'permissionError', 'description': 'You are not the owner of this room'}, room=sid)
  else:
    message = bleach.clean(message, tags=['b', 'i', 'a', 'u', 's'])
    await distribute_message(message, sid, room['room'], dataid)

# This is a seperate function that sends out the final message from the last function
# This function is triggered if the message didn't contain a blocking command, and passed all
# the checks.
async def distribute_message(message, sid, room, data):
  global latest_id
  username = await validate_sid(sid)
  if not username:
    return
  userColor = 'user'
  if username in ADMIN_LIST:
    userColor = 'admin'
  elif username == 'BuffMANs':
    userColor = 'mans'
  try:
    latest_id = load_room(room)['messages'][-1]['id'] + 1
  except(IndexError):
    latest_id = 1
  # Don't even try to wrap your head around the code to parse
  # file uploads. Just leave it, it's not worth trying to change.
  # If you are trying to change it, then you'll need to change it 
  # alongside the dataSend() function.
  if data and active_upload_keys[data].split("!&")[0] != 'omtheme' and active_upload_keys[data].split("!&")[0] != 'omext':
    attachments = f'<{active_upload_keys[data].split("!&")[0]} class=imgAttachment src=https://{CDN_DOMAIN}/{room}/{data}/{active_upload_keys[data].split("!&")[1]} height=300px></{active_upload_keys[data].split("!&")[0]}>'
  elif data and active_upload_keys[data].split("!&")[0] == 'omtheme':
    jsondata = json.loads(active_upload_keys[data].split("!&")[2])
    themeKey = uuid.uuid4()
    # Now this is what I call "server-side rendering"!
    attachments = f'<div class=omThemePre><div class=colorPre style="background-color:{jsondata["background"]};"><pre></pre></div><div class=colorPre style="background-color:{jsondata["highlight"]};"><pre></pre></div><div class=colorPre style="background-color:{jsondata["accent"]};"><pre></pre></div><p class=fileTitle>Theme</p><p class=themeName>' + jsondata["name"].replace("'", r"&#39;") + f'</p><input type=hidden id={themeKey}data value=\'' + active_upload_keys[data].split("!&")[2].replace("'", r"&#39;") + f'\'><button id={themeKey}button class=applyTheme onclick="javascript: extData=JSON.parse(document.getElementById(\'{themeKey}data\').value); spawnPopup();">Apply</button></div>'
  elif data and active_upload_keys[data].split("!&")[0] == 'omext':
    jsondata = json.loads(active_upload_keys[data].split("!&")[2])
    extKey = uuid.uuid4()
    attachments = f'<div class=omThemePre><p class=fileTitle>Extension</p><p class=themeName>' + jsondata["name"].replace("'", r"&#39;") + f'</p><br><p class=themeDesc>' + jsondata["description"].replace("'", r"&#39;") + f'</p><input type=hidden id={extKey}data value=\'' + active_upload_keys[data].split("!&")[2].replace("'", r"&#39;") + f'\'><button id={extKey}button class=applyTheme onclick="javascript: extData=JSON.parse(document.getElementById(\'{extKey}data\').value); spawnPopup();">Apply</button></div>'
  else:
    attachments = False
  await sio.emit('msgDist', {'content': marko.convert(message), 'author': username, 'color': userColor, 'timestamp': str(datetime.datetime.utcnow().isoformat()), 'id': latest_id, 'attachments': attachments}, room=room)
  room_data = load_room(room)
  room_data['messages'].append({'content': marko.convert(message), 'author': username, 'color': userColor, 'timestamp': str(datetime.datetime.utcnow().isoformat()), 'id': latest_id, 'attachments': attachments})
  save(room_data, load('rooms')[room])

# This is an endpoint that checks the user's provided account details, and if all checks
# pass, adds it to the user DB. It's basically just a large block of if statements.
@sio.event
async def register_account(sid, username, password):
  username_chars = list(username)
  for char in username_chars:
    if char not in alphanumeric_list:
      await sio.emit('statusCallback', {'error': 'alphanumericError', 'description': 'Usernames can only contain alphanumeric characters, underscores (_), and dashes (-).'}, room=sid)
      return
  userStore = load('userIndex')
  if username in userStore:
    await sio.emit('statusCallback', {'error': 'duplicateUsernameError', 'description': 'Username already taken'}, room=sid)
    return
  elif len(username) > 30:
    await sio.emit('statusCallback', {'error': 'usernameTooLong', 'description': 'Max username length is 30 characters'}, room=sid)
    return
  elif len(password) > 50:
    await sio.emit('statusCallback', {'error': 'passwordTooLong', 'description': 'Max password length is 50 characters'}, room=sid)
    return
  elif len(username) == 0:
    await sio.emit('statusCallback', {'error': 'usernameTooShort', 'description': 'Usernames cannot be empty'}, room=sid)
    return
  elif len(password) < 5:
    await sio.emit('statusCallback', {'error': 'passwordTooShort', 'description': 'Passwords must be above 5 characters'}, room=sid)
    return
  elif predict_prob([username]) > [0.9]:
    await sio.emit('statusCallback', {'error': 'profanityFilter', 'description': 'Your username had a profanity probability greater than the threshold of 90%. As such, your message has been deleted.'}, room=sid)
    return
  if username in load('banned'):
    await sio.emit('statusCallback', {'error': 'bannedUser', 'description': 'This username belongs to a previously banned user.'}, room=sid)
    return
  user_uid = str(uuid.uuid4())
  userStore[username] = user_uid
  save(userStore, 'userIndex')
  password = password.encode('utf-8')
  encrypt = bcrypt.hashpw(password, bcrypt.gensalt(10))
  b64_encode = base64.b64encode(encrypt)
  b64_string = b64_encode.decode('utf-8')
  data = {'password': b64_string}
  save(data, user_uid)
  validSids[sid] = username
  await sio.emit('statusCallback', {'status': 'accountCreated'}, room=sid)
  await sio.emit('statusCallback', {'popup': 'Success!', 'description': 'Your account has been successfully created!'}, room=sid)

# This is the login function. It verifies the user's account credentials, and
# checks their password with the one stored in the DB. Don't worry, as of the
# code rewrite, this is all encrypted.
@sio.event
async def login(sid, username, password):
  if username in load('banned'):
    await sio.emit('statusCallback', {'error': 'bannedUserError', 'description': 'You have been banned from participating in this chatroom.'}, room=sid)
    return
  userStore = load('userIndex')
  password = password.encode('utf-8')
  if username in userStore and bcrypt.checkpw(password, base64.b64decode(load(userStore[username])['password'])):
    validSids[sid] = username
    await sio.emit('statusCallback', {'status': 'accountLogin'}, room=sid)
    return
  await sio.emit('statusCallback', {'error': 'accountLoginError', 'description': 'The desired account does not exist, or you used an incorrect password.'}, room=sid)

# Type indicators are currently broken.
@sio.event
async def amTyping(sid):
  rm = await sio.get_session(sid)
  username = await validate_sid(sid)
  if not username:
    return
  await sio.emit('userTyping', username, room=rm['room'])

# Takes a temp key given from a 2fa key and changes the password of the associated user
@sio.event
async def change_password(sid, key, password):
  print(temp_pass_keys)
  print(key)
  for keyb in temp_pass_keys:
    if keyb[1] == key:
      username = keyb[0]
      temp_pass_keys.pop(temp_pass_keys.index(keyb))
      userStore = load('userIndex')
      user_data = load(userStore[username])
      user_data['password'] = password
      save(user_data, userStore[username])
      await sio.emit('statusCallback', {'popup': 'passwordSuccess', 'description': 'Successfully changed your password!'}, room=sid)
      return
  else:
    await sio.emit('statusCallback', {'error': 'invalidTwoKey', 'description': 'You must validate your identity with a 2fa key before changing password.'}, room=sid)
    return

# Validates a user's provided 2fa key
@sio.event
async def validate_2fa(sid, key):
  for secret in secretStore:
    tempotp = pyotp.TOTP(secretStore[secret])
    if tempotp.verify(key):
      twokey = str(uuid.uuid4())
      username = secret
      temp_pass_keys.append([username, twokey])
      await sio.emit('twoKey', {'key': twokey, 'status': 'success'}, room=sid)
  else:
    await sio.emit('twoKey', 'invalidkey', room=sid)
    return

# Enables 2fa for a user by generating a QR code for them and storing their secret
@sio.event
async def enable_2fa(sid):
  username = await validate_sid(sid)
  if not username:
    return
  secret = pyotp.random_base32()
  secretStore[username] = secret
  with open('secret.store', 'wb') as secretStoreSave:
    pickle.dump(secretStore, secretStoreSave)
  
  code = qrcode.make(pyotp.totp.TOTP(secret).provisioning_uri(name=f'{username}@openmessenger', issuer_name='OpenMessage'))
  code.save('tmp.png')
  with open('tmp.png', 'rb') as image:
    imaged = image.read()
    await sio.emit('sendQR', {'qrcode': str(base64.b64encode(imaged)).replace("b'", '').replace("'", ''), 'contains': '2fa'}, room=sid)
  image.close()

# Checks if the user emitting this event has 2fa enabled
@sio.event
async def has_2fa(sid):
  username = await validate_sid(sid)
  if not username:
    return
  if username in secretStore:
    await sio.emit('does2fa', True, room=sid)
  else:
    await sio.emit('does2fa', False, room=sid)

# sends the message history to the given SID#, this is just a function for readability.
async def getHistory(sid, rm):
  await sio.emit('messageHistory', load_room(rm)['messages'], room=sid)

# same as the above function, but it sends the updated message history to everyone
# in the room. This is called when messages are deleted or edited.
# Yes, this means the user recieves the entire room's message history
# when a message is edited or deleted, instead of just updating a single message.
# This is going to be changed shortly.
async def getHistoryAll(rm):
  await sio.emit('messageHistory', load_room(rm)['messages'], room=rm)

# This starts the ratelimiter counter, which counts down the # of messages a user has sent.
# This is required, without it you would send 2 messages and be permanently ratelimited.
loop = asyncio.get_event_loop()
loop.create_task(ratelimiter())

# starts the uvicorn server without CLI options. This is requred for systemd compatibility.
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=SERVER_PORT, log_level="info")