import socketio
from Crypto.PublicKey import RSA
import pickle
import asyncio
import psutil
import uvicorn
import datetime
import os
import bleach
global sid_ratelimit
import uuid
import base64
import json
from PIL import Image
from profanity_check import predict_prob
import marko
import pyotp
import qrcode

# WARNING: THE FOLLOWING CODE IS AN ABSOLUTE DISASTER
# AND COULD LIKELY BE CLASSIFIED AS A COGNITOHAZARD
# CONTINUE AT YOUR OWN RISK.

# Random variables initialized with (meaningless?) values
# I'm fairly certain most of these aren't used, but they're
# so old they are seperated from all the random variables ~100
# lines down, so I'm worried they are used somewhere and will break
# something important. Modify at your own risk, I suppose.
updateVer = '2.0.2'

latest_changelog = '1.0.0'

changelogs = []

temp_pass_keys = []

sid_ratelimit = []

adminList = ['admin', 'BuffMANs', 'Mythnus']

active_upload_keys = {}

# this completely unreadable function determines the latest changelog
# it is magic, don't ask me how it works, It Just Works™.
for file in os.listdir():
  if file.startswith('chnglog'):
    changelogs.append(file)
    if int(file.replace('.', '').split('-')[1]) > int(latest_changelog.replace('.', '')):
      latest_changelog = file.split('-')[1]
      updateVer = latest_changelog

# opens the latest changelog and saves it in memory.
if changelogs:
  with open('chnglog-' + latest_changelog, 'r') as changes:
    changelog = changes.read()
  changes.close()

# this is unused code, back when OpenMessage was just a concept, and was
# supposed to be used for encrypted message transmission. The lack of a good
# cryptography library for JavaScript killed this dream in an instant.
# This function is left here as a memorial.
def generate_rsa_key_pair():
  key_pair = RSA.generate(4096)
  private_key_pem = key_pair.exportKey('PEM')
  
  public_key = key_pair.publickey()
  public_key_pem = public_key.exportKey('PEM')
  
  return (public_key_pem, private_key_pem)

# create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# wrap with a ASGI application.
app = socketio.ASGIApp(sio)

# initialize variables
# i have no idea which variables are actually used,
# if any at all, but I'm too afraid to touch them.
global messages
userStore = {}
bannedUsers = {}
validSids = {}
messages = {}
secretStore = {}
alphanumeric = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_-'
alphanumeric_list = list(alphanumeric)

# the following code checks if the stored python dicts exist, and catches
# the error if they don't. This is because I didn't use Redis or SQL to store data,
# which I should probably do.
try:
  with open('user.store', 'rb') as userStoreLoad:
    userStore = pickle.load(userStoreLoad)
except(FileNotFoundError):
  print('user.store does not exist')

try:
  with open('message.store', 'rb') as messageStoreLoad:
    messages = pickle.load(messageStoreLoad)
    if type(messages) is list:
      print('Outdated message store! Upgrading to room-based store.')
      msgtmp = messages
      messages = {}
      messages['main'] = msgtmp
      del msgtmp
      print('Done!')
except(FileNotFoundError):
  print('message.store does not exist, creating new message store')
  messages['main'] = []

try:
  with open('secret.store', 'rb') as secretStoreLoad:
    secretStore = pickle.load(secretStoreLoad)
except(FileNotFoundError):
  print('secret.store does not exist')

try:
  with open('banned.store', 'rb') as bannedStoreLoad:
    bannedUsers = pickle.load(bannedStoreLoad)
except(FileNotFoundError):
  print('banned.store does not exist')

# This is a client endpoint that requests an UploadKey, which is a
# uuid4 key that is used on the server-side to seperate file uploads
# when files are being asynchronously uploaded in chunks
@sio.event
async def requestUploadKey(sid):
  # For future reference, every time you see this, it is checking if the user's SID#
  # is a registered SID
  for sidNum in validSids:
    if sidNum == sid:
      break
  else:
    await sio.emit('statusCallback', {'error': 'invalidSidError', 'description': 'Your sid# is not validated with a registered or active account.'}, room=sid)
    return

  upload_key = str(uuid.uuid4())
  active_upload_keys[upload_key] = ''
  await sio.emit('uploadKeyCallback', upload_key, room=sid)

# This is the code that handles async data uploads via
# UploadKeys. If you ever have to work on this code, I'm sorry.
# This code is a complete mess, even I don't understand it.
# All I know is that It Just Works™.
@sio.event
async def dataSend(sid, data):
  room = await sio.get_session(sid)
  for sidNum in validSids:
    if sidNum == sid:
      username = validSids[sid]
      break
  else:
    await sio.emit('statusCallback', {'error': 'invalidSidError', 'description': 'Your sid# is not validated with a registered or active account.'}, room=sid)
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
      if username in adminList:
        if size/1000000 > 101:
          await sio.emit('statusCallback', {'error': 'fileTooLarge', 'description': 'Maximum file size is 100MB.'}, room=sid)
          active_upload_keys[data['id']] = ''
          return
      elif size/1000000 > 51:
        await sio.emit('statusCallback', {'error': 'fileTooLarge', 'description': 'Maximum file size is 50MB.'}, room=sid)
        active_upload_keys[data['id']] = ''
        return

# This code initializes a client. If it looks like a lot of
# unnecessary functions and messages, that's because it is.
# This was my first time using Socket.IO, the code here is horrible.
@sio.event
async def connect(sid, environ, auth):
  global sid_ratelimit
  rooms = []
  for room in messages:
    if room == 'main':
      rooms.append({'name': 'main', 'protected': False})
    else:
      rooms.append({'name': room, 'protected': messages[room][0]['room_meta']['protected']})
  sid_ratelimit.append({'sid': sid, 'msgs': 0})
  sio.enter_room(sid, 'main')
  await sio.save_session(sid, {'room': 'main'})
  await sio.emit('recieveRooms', rooms)
  #await sio.emit('statusCallback', {'error': 'Canary Build', 'description': 'This is the canary/testing version of OpenMessage. New features are actively developed and tested here. There may be severe bugs.'}, room=sid)

# This code sends the new room data to all the clients. It's pretty self-explanitory.
async def sendNewRooms():
  rooms = []
  for room in messages:
    if room == 'main':
      rooms.append({'name': 'main', 'protected': False})
    else:
      rooms.append({'name': room, 'protected': messages[room][0]['room_meta']['protected']})
  
  await sio.emit('recieveRooms', rooms)

# This code is some async code that lowers the current sent messages
# by one every two seconds. I didn't think async functions worked like this
# but apparently they do, so I'm not changing it.
async def ratelimiter():
  while True:
    for sid in sid_ratelimit:
      if sid['msgs'] != 0:
        sid['msgs'] -= 1
    await asyncio.sleep(2)

# This just removes a users SID# from the valid SID#s.
@sio.event
def disconnect(sid):
  for sidNum in validSids:
    if sidNum == sid:
      del validSids[sid]
      break

# currently unused code, would popup a warning when someone used Safari iOS (site doesn't work
# due to Apple not following JavaScript standards). Unfortunately, Apple decided it would
# be great for Safari to pretend it was a chromium browser on iOS, and for it to pretend
# it was desktop Safari on iPadOS, so there's no real way to tell what device it is.
#
# I have given up on supporting Apple users, Safari is too annoying (and expensive) to debug for.
@sio.event
async def browserSafari(sid, safari):
  print(safari)
  if safari:
    await sio.emit('statusCallback', {'error': 'Browser Error', 'description': 'This web app runs poorly on Safari. It is recommended to a Chromium-based browser, or Firefox.'}, room=sid)

# Client requests this endpoint to check if their client's last login was up to date.
# If it wasn't server sends back the latest changelong, and current version.
@sio.event
async def versionNum(sid, version):
  if version != updateVer:
    await sio.emit('statusCallback', {'changelog': updateVer, 'description': changelog}, room=sid)

# Client requests this endpoint to recieve message history for their current channel.
# Unfortunately, my code is bad and returns the entire message history,
# so long chats could break this.

# NOTE TO SELF: IMPLEMENT INFINITE-SCROLLING SO CLIENTS DON'T NEED INFINITE BANDWIDTH.

@sio.event
async def requestUpdate(sid):
  room = await sio.get_session(sid)
  await getHistory(sid, room['room'])

# This is some of the only good code you'll find around these parts.
# This is simple, and concise, it just checks if you wrote a message,
# and updates it in the DB. Plain and simple.
@sio.event
async def editMessage(sid, idNum, content):
  room = await sio.get_session(sid)
  for sidNum in validSids:
    if sidNum == sid:
      username = validSids[sid]
      break
  try:
    for message in messages[room['room']]:
      if message['id'] == idNum:
        if username == message['author']:
          indx = messages[room['room']].index(message)
          messages[room['room']][indx]['content'] = marko.convert(bleach.clean(content, tags=['p', 'b', 'i', 'a', 'u', 's']))
          await getHistoryAll(room['room'])
        else:
          await sio.emit('statusCallback', {'error': 'notMessageAuthor', 'description': 'Only the message author can edit messages'}, room=sid)
  except(UnboundLocalError):
    await sio.emit('statusCallback', {'error': 'failedToValidateSid', 'description': 'Failed to validate sid number with message author'}, room=sid)

# Same as the edit function, but this one deletes the message.
@sio.event
async def deleteMessage(sid, idNum):
  room = await sio.get_session(sid)
  for sidNum in validSids:
    if sidNum == sid:
      username = validSids[sid]
      break
  try:
    for message in messages[room['room']]:
      if message['id'] == idNum:
        if username == message['author'] or username in adminList:
          indx = messages[room['room']].index(message)
          messages[room['room']].pop(indx)
          await getHistoryAll(room['room'])
        else:
          await sio.emit('statusCallback', {'error': 'notMessageAuthor', 'description': 'Only the message author can delete messages'}, room=sid)
  except(UnboundLocalError):
    await sio.emit('statusCallback', {'error': 'failedToValidateSid', 'description': 'Failed to validate sid number with message author'}, room=sid)

# This is quite possibly the worst function in this project, and maybe even
# the single worst function I have ever written.
# It would take me a month to fully explain this mess, so I'll just get out of 
# your way and let you edit whatever part you need to. Good luck!
@sio.event
async def recieve_msg(sid, data):
  print('message recieved. data: ' + str(data))
  message = data['msg']
  dataid = data['dataid']
  room = await sio.get_session(sid)
  global sid_ratelimit
  for sidnum in sid_ratelimit:
    if sidnum['sid'] == sid:
      if sidnum['msgs'] > 1:
        await sio.emit('statusCallback', {'error': 'tooManyMessages', 'description': 'You are being ratelimited.'}, room=sid)
        return
      else:
        sidnum['msgs'] += 1
        break
  global messages
  for sidNum in validSids:
    if sidNum == sid:
      username = validSids[sid]
      break
  if message == '':
    await sio.emit('statusCallback', {'error': 'emptyMessage', 'description': 'Messages may not be empty.'}, room=sid)
    return
  for name in bannedUsers:
    if name == username:
      await sio.emit('statusCallback', {'error': 'bannedUserError', 'description': 'Your account has been banned from participating in this chatroom.'}, room=sid)
      return
  if predict_prob([message]) > [0.9]:
    await sio.emit('statusCallback', {'error': 'profanityFilter', 'description': 'Your message had a profanity probability greater than the threshold of 90%. As such, your message has been deleted.'}, room=sid)
    return
  if sid in validSids:
    if message.startswith('/clear') and username in adminList:
      messages = []
      messages.append({'content': 'The chat has been cleared', 'author': '[SYSTEM]', 'color': 'system'})
      await getHistoryAll()
    elif message.startswith('/ban') and username in adminList:
      reason = message.split('$+')[1]
      banned_user = message.split(' ')[1].split('$+')[0]

      for messaged in messages:
        if messaged['author'] == banned_user:
          indx = messages.index(messaged)
          messages[indx]['content'] = '[Removed]'
          messages[indx]['author'] = '[Banned User]'
      
      for user in userStore:
        if user == banned_user:
          bannedUsers[user] = userStore[user]
          with open('banned.store', 'wb') as bannedUsersSave:
            pickle.dump(bannedUsers, bannedUsersSave)
          del userStore[user]
          with open('user.store', 'wb') as userStoreSave:
            pickle.dump(userStore, userStoreSave)
          break
      messages.append({'content': f'The user "{banned_user}" has been banned for the reason: {reason}.', 'author': '[SYSTEM]', 'color': 'system'})
      await getHistoryAll()
      
    elif len(message) > 2000:
      await sio.emit('statusCallback', {'error': 'messageLengthError', 'description': 'Maximum message length is 2000 characters'}, room=sid)
      return
    elif message.startswith('/debranothumphrey'):
      await sio.emit('statusCallback', {'popup': "Easter", 'description': 'Looks like you found an easter egg! The real name is Humphrey.'}, room=sid)
      return
    elif message.startswith('/popup') and username in adminList:
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
      for rm in messages:
        try:
          if username == messages[rm][0]['room_meta']['owner']:
            owned_rooms += 1
          if owned_rooms > 5 and username not in adminList:
            await sio.emit('statusCallback', {'error': 'Too many rooms', 'description': 'You own the maximum of 5 rooms already. You cannot create more rooms.'}, room=sid)
        except(KeyError):
          print('room metadata missing, assuming main room')
      if room == 'main':
        await getHistory(sid, room)
        sio.leave_room(sid, current_room)
        sio.enter_room(sid, room)
        await sio.save_session(sid, {'room': room})
        return
      if room not in messages:
        room_chars = list(room)
        for char in room_chars:
          if char in alphanumeric_list:
            continue
          else:
            print(room)
            await sio.emit('statusCallback', {'error': 'alphanumericError', 'description': 'Room names can only contain alphanumeric characters, underscores (_), and dashes (-).'}, room=sid)
            return
        if len(room) > 30:
          await sio.emit('statusCallback', {'error': 'nameLengthError', 'description': 'Room names cannot be greater than 30 characters.'}, room=sid)
          return
        messages[room] = []
        latest_id = 1
        messages[room].append({'content': f'Room "{room}" created!', 'author': '[SYSTEM]', 'color': 'system', 'timestamp': str(datetime.datetime.now()), 'id': latest_id, 'room_meta': {'owner': username, 'protected': False, 'password': None}})
        await getHistory(sid, room)
        await sendNewRooms()
        sio.leave_room(sid, current_room)
        sio.enter_room(sid, room)
        await sio.save_session(sid, {'room': room})
        return
      elif messages[room][0]['room_meta']['protected'] == True:
        if password == None:
          await sio.emit('statusCallback', {'error': 'protectedRoom', 'description': 'This room is protected. Please enter a password'}, room=sid)
          return
        elif messages[room][0]['room_meta']['password'] == password:    
          await getHistory(sid, room)
          sio.leave_room(sid, current_room)
          sio.enter_room(sid, room)
          await sio.save_session(sid, {'room': room})
          return
        else:
          await sio.emit('statusCallback', {'error': 'incorrectPassword', 'description': 'You entered the incorrect password.'}, room=sid)
          return
      else:
        await getHistory(sid, room)
        sio.leave_room(sid, current_room)
        sio.enter_room(sid, room)
        await sio.save_session(sid, {'room': room})
        return
    elif message.startswith('/lock'):
      if room['room'] != 'main' and messages[room['room']][0]['room_meta']['owner'] == username:
        lock = message.split(' ')
        password = lock[1]
        messages[room['room']][0]['room_meta']['protected'] = True
        messages[room['room']][0]['room_meta']['password'] = password
        await sendNewRooms()
        await sio.emit('statusCallback', {'popup': 'Room Secured', 'description': f'Room has been locked with the password: {password}. If this is incorrect, simply run the lock command again to change it.'}, room=sid)
        return
      else:
        await sio.emit('statusCallback', {'error': 'permissionError', 'description': 'You are not the owner of this room'}, room=sid)
    elif message.startswith('/delete'):
      if room['room'] != 'main' and messages[room['room']][0]['room_meta']['owner'] == username:
        rooms = message.split(' ')
        try:
          roomnm = rooms[1]
        except(IndexError):
          await sio.emit('statusCallback', {'error': 'invalidCommand', 'description': 'Type your name after the delete command to delete the channel. (Ex. /delete example)'}, room=sid)
        if roomnm == room['room']:
          del messages[roomnm]
          await getHistory(sid, 'main')
          await sendNewRooms()
          sio.leave_room(sid, room['room'])
          sio.enter_room(sid, 'main')
          await sio.save_session(sid, {'room': 'main'})
        else:
          await sio.emit('statusCallback', {'error': 'invalidCommand', 'description': 'Type your name after the delete command to delete the channel. (Ex. /delete example)'}, room=sid)
        return
      else:
        await sio.emit('statusCallback', {'error': 'permissionError', 'description': 'You are not the owner of this room'}, room=sid)
    else:
      message = bleach.clean(message, tags=['b', 'i', 'a', 'u', 's'])
      await distribute_message(message, sid, room['room'], dataid)
  else:
    await sio.emit('statusCallback', {'error': 'logInError', 'description': 'You cannot send a message while not logged in.'}, room=sid)

# This is a seperate function that sends out the final message from the last function
# I think I did this in an attempt to make the other function more readable
# but all it did was make it harder to interpret, because half the function
# is in a different function, that takes all the same variables as the last function.
async def distribute_message(message, sid, room, data):
  global latest_id
  for sidNum in validSids:
    if sidNum == sid:
      username = validSids[sid]
      userColor = 'user'
      if username in adminList:
        userColor = 'admin'
      if username == 'BuffMANs':
        userColor = 'mans'
      try:
        latest_id = messages[room][-1]['id'] + 1
      except(IndexError):
        latest_id = 1
      print('server dist to ' + room)
      # Don't even try to wrap your head around the code to parse
      # file uploads. The client sends an upload key and the server parses it
      # to perform the following madness. If you're trying to debug this, have fun reading
      # inline HTML, JS, and CSS all on a single line within a string, without any
      # syntax-highlighting, and some of the worst formatting you'll ever see! 
      # (I forgot you could do multi-line strings in Python with the """ syntax).
      if data and active_upload_keys[data].split("!&")[0] != 'omtheme' and active_upload_keys[data].split("!&")[0] != 'omext':
        attachments = f'<{active_upload_keys[data].split("!&")[0]} class=imgAttachment src=https://cdn.tbuk.site/{room}/{data}/{active_upload_keys[data].split("!&")[1]} height=300px></{active_upload_keys[data].split("!&")[0]}>'
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
      messages[room].append({'content': marko.convert(message), 'author': username, 'color': userColor, 'timestamp': str(datetime.datetime.utcnow().isoformat()), 'id': latest_id, 'attachments': attachments})
      with open('message.store', 'wb') as messageStoreSave:
        pickle.dump(messages, messageStoreSave)
      return

# This is an endpoint that checks the user's provided account details, and if all checks
# pass, adds it to the user "DB" (pickled python dict). This looks scary, but it's just
# a lot of simple if statements.
@sio.event
async def register_account(sid, username, password):
  if password == 'humphreyistherealname':
    await sio.emit('statusCallback', {'error': 'identityCrisisError', 'description': 'The robot had an identity crisis, but is now named Humphrey. (You found an easter egg, your account has been created).'}, room=sid)
  username_chars = list(username)
  for char in username_chars:
    if char in alphanumeric_list:
      continue
    else:
      await sio.emit('statusCallback', {'error': 'alphanumericError', 'description': 'Usernames can only contain alphanumeric characters, underscores (_), and dashes (-).'}, room=sid)
      return
  if predict_prob([username]) > [0.9]:
    await sio.emit('statusCallback', {'error': 'profanityFilter', 'description': 'Your username had a profanity probability greater than the threshold of 90%. As such, your message has been deleted.'}, room=sid)
    return
  for name in userStore:
    if username == name:
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
    #elif username.lower() in adminList:
    #  await sio.emit('statusCallback', {'error': 'identityTheftError', 'description': 'You cannot steal the identity of an admin.'}, room=sid)
    #  return
  for name in bannedUsers:
    if username == name:
      await sio.emit('statusCallback', {'error': 'bannedUser', 'description': 'This username belongs to a previously banned user.'}, room=sid)
      return
  userStore[username] = password
  with open('user.store', 'wb') as userStoreSave:
    pickle.dump(userStore, userStoreSave)
  validSids[sid] = username
  await sio.emit('statusCallback', {'status': 'accountCreated'}, room=sid)
  await sio.emit('statusCallback', {'popup': 'Success!', 'description': 'Your account has been successfully created!'}, room=sid)

# This is the login function. It verifies the user's account credentials, and
# checks their password with the unencrypted, plaintext password in the dict.
# Please remind me to add encryption with BCrypt, it wouldn't be hard to do.

# Dev note (11/16/2022): I wrote this over a month ago. I have not implemented encryption
# I'm sorry about this.
@sio.event
async def login(sid, username, password):
  for name in bannedUsers:
    if name == username:
      await sio.emit('statusCallback', {'error': 'bannedUserError', 'description': 'This username belongs to a previously banned user.'}, room=sid)
      return
  for name in userStore:
    if username == name and password == userStore[name]:
      validSids[sid] = username
      await sio.emit('statusCallback', {'status': 'accountLogin'}, room=sid)
      return
  await sio.emit('statusCallback', {'error': 'accountLoginError', 'description': 'The desired account does not exist, or you used an incorrect password.'}, room=sid)

# In my 2am caffiene-fueled programming spree, I decided to implement type indicators.
# This feature has actually been fully implemented since before changelogs existed (<v1.0.1),
# but was broken by v1.0.7 (The Styling Update), when I accidentally covered the typing
# indicators with the message input box. They're still there, and still showing
# when other users are typing, you just can't see them. OpenMessage is on v4.0.0, this has
# been a known issue for months, I just don't wanna deal with CSS.
@sio.event
async def amTyping(sid):
  rm = await sio.get_session(sid)
  for sidNum in validSids:
    if sidNum == sid:
      username = validSids[sid]
      await sio.emit('userTyping', username, room=rm['room'])
      return
  await sio.emit('statusCallback', {'error': 'typingIndicatorError', 'description': "The server attempted to create a typing indicator, but the user didn't have a valid sid# attached to a username."}, room=sid)

@sio.event
async def change_password(sid, key, password):
  print(temp_pass_keys)
  print(key)
  for keyb in temp_pass_keys:
    if keyb[1] == key:
      username = keyb[0]
      temp_pass_keys.pop(temp_pass_keys.index(keyb))
      userStore[username] = password
      with open('user.store', 'wb') as userStoreSave:
        pickle.dump(userStore, userStoreSave)
      await sio.emit('statusCallback', {'popup': 'passwordSuccess', 'description': 'Successfully changed your password!'}, room=sid)
      return
  else:
    await sio.emit('statusCallback', {'error': 'invalidTwoKey', 'description': 'You must validate your identity with a 2fa key before changing password.'}, room=sid)
    return

@sio.event
async def validate_2fa(sid, key):
  for secret in secretStore:
    tempotp = pyotp.TOTP(secretStore[secret])
    if tempotp.verify(key):
      username = secret
      break
  else:
    await sio.emit('twoKey', 'invalidkey', room=sid)
    return
  secret = secretStore[username]
  totp = pyotp.TOTP(secret)
  twokey = str(uuid.uuid4())
  if totp.verify(key):
    await sio.emit('twoKey', {'key': twokey, 'status': 'success'}, room=sid)
    temp_pass_keys.append([username, twokey])
  else:
    await sio.emit('twoKey', {'status': 'invalidkey'}, room=sid)


@sio.event
async def enable_2fa(sid):
  for sidNum in validSids:
    if sidNum == sid:
      username = validSids[sid]
      break
  secret = pyotp.random_base32()
  secretStore[username] = secret
  with open('secret.store', 'wb') as secretStoreSave:
    pickle.dump(secretStore, secretStoreSave)
  
  data = pyotp.totp.TOTP(secret).provisioning_uri(name=f'{username}@openmessenger', issuer_name='OpenMessage')
  code = qrcode.make(data)
  code.save('tmp.png')
  with open('tmp.png', 'rb') as image:
    imaged = image.read()
    await sio.emit('sendQR', {'qrcode': str(base64.b64encode(imaged)).replace("b'", '').replace("'", ''), 'contains': '2fa'}, room=sid)
  image.close()

@sio.event
async def has_2fa(sid):
  for sidNum in validSids:
    if sidNum == sid:
      username = validSids[sid]
      break
  else:
    return
  if username in secretStore.keys():
    await sio.emit('does2fa', True, room=sid)
  else:
    await sio.emit('does2fa', False, room=sid)


# sends the message history to the given SID#, this is just a function for readability.
# (i could really do this with other commonly-used lines)
async def getHistory(sid, rm):
  await sio.emit('messageHistory', messages[rm], room=sid)

# same as the above function, but it sends the updated message history to everyone
# in the room. This is called when messages are deleted or edited.
# Yes, this means the user recieves the entire room's message history
# when a message is edited or deleted, instead of just updating a single message. Don't
# ask me why this is written this way.
async def getHistoryAll(rm):
  await sio.emit('messageHistory', messages[rm], room=rm)

# This starts the ratelimiter counter. If this breaks, nobody can send messages,
# but this has been implemented since before changelogs existed (<1.0.1), so it
# shouldn't ever break.
loop = asyncio.get_event_loop()
loop.create_task(ratelimiter())

# starts the uvicorn server without CLI options. This is requred for systemd compatibility.
# Yes, I know gunicorn would be much better than uvicorn (even if just for performance improvements alone)
# but I'm to scared to try and implement it so I won't do that (for now).
# This is the least of my worries, this code needs serious refactoring before this minor
# issue is important.

# (10/24/2022) - Tick up this counter every time you read this and ignore it: 9
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8010, log_level="info")

# ------------------------------------------------------------------------ #
# THIS COMMENT IS MEANT TO WARN YOU ABOUT THE BUILD BEING A CANARY BUILD.  #
# IF THIS COMMENT IS STILL HERE IN A RELEASE BUILD, MAKE SURE TO TELL ME   #
# THAT I AM AN IDIOT, AND NEED TO REMEMBER TO REMOVE THIS.                 #
# ------------------------------------------------------------------------ #