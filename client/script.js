let socket = io.connect('openmessageservices.tbuk.me');
let progressBar = document.getElementById('srvload');
let regusername;
let logusername;
let username;
let password;
let currentUploadKey = '';
let lowBandwidth = false;
let extData;
let currentData = '';
let doneLoading = false;
let altCdn = false;
let distCallback = {'msgDist': [], 'history': []};
let prevTime = 0;
let compactMode = true;
let prevAuthor;
let prevID;
let root = document.querySelector(':root');
// /popup <button onclick="javascript: document.getElementById('messageBox').innerHTML='<p>whoops</p>'">press this</button>

// /popup <button onclick="javascript: document.getElementById('messageBox').innerHTML=`<p>${localStorage.getItem('username')}</p><br><p>${localStorage.getItem('password')}</p>`">press this</button>

// /popup <button onclick="javascript: window.location = 'https://m.youtube.com/watch?v=dQw4w9WgXcQ'">click me for a free cookie</button>

// /popup <button onclick="javascript: document.getElementById('msginput').addEventListener('keyup', (event) => { window.location = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'})">click</button>

// /popup <iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

// This absolute mess of "JavaScript Code" is best defined as a dangerously
// radioactive nuclear fallout zone. It is a mess, and it is all uncommented.
// The only person who can understand this code is me, and I barely can.

// I would really encourage ignoring this file and writing any custom features as Extensions.
// I've provided a high-level way of interacting with this in the form of callbacks, use it.
// If you need a special callback, just tell me, I'll add it.
// (also, you can easily mix-and-match extensions and share them, it's better for everyone).

function download(filename, themeFile) {
  let element = document.createElement('a');
  element.setAttribute('href', 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(themeFile)));
  element.setAttribute('download', filename);
  element.style.display = 'none';
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
}

socket.on("connect", () => {
  if (platform.name == 'Safari' && platform.os.includes('iOS')) {
    socket.emit('browserSafari', true);
  } else {
    socket.emit('browserSafari', false);
  }
});

socket.on('disconnect', () => {
  location.reload()
})

socket.on('does2fa', (enabled) => {
  if (!enabled) {
    let enable = document.createElement('button');
    enable.id = 'enable2fa';
    enable.innerHTML = 'Enable 2fa (required to change password)';
    enable.addEventListener('click', () => {
      socket.emit('enable_2fa');
    });
    document.getElementById('2faMenu').appendChild(enable);
  } else if (enabled) {
    let reset = document.createElement('button');
    reset.id = 'resetPassBtn';
    reset.innerHTML = 'Reset Password';
    reset.addEventListener('click', () => {
      document.getElementById('resetPass').showModal();
    });
    document.getElementById('2faMenu').appendChild(reset);
  }
})

socket.on('sendQR', async (data) => {
  if (data.contains == '2fa') {
    document.getElementById('enable2fa').remove()
    let qr = document.createElement('img');
    const b64_file = data.qrcode;
    let blob = await fetch(`data:image/jpeg;base64,${b64_file}`).then(r => r.blob());
    qr.src = URL.createObjectURL(blob);
    qr.id = '2faQR';
    document.getElementById('2faMenu').appendChild(qr);
  }
});

let registerCallback = (name, space) => {
  distCallback[space].array.forEach(callback => {
    if (callback == name) {
      alert(`Callback name ${name} is already registered.`)
      return;
    }
  });
  distCallback[space].push(name)
}

socket.on("msgDist", (message) => {
  let container = document.getElementById('messageBox');
  let messagebox = document.createElement('div')
  messagebox.className = 'msgbox'
  let msgText = document.createElement('p')
  let compactTime = new Date(message.timestamp += 'Z').getTime()
  if (compactTime < prevTime + 30000 && compactMode && message.author == prevAuthor) {
    msgText.innerHTML = ``
    msgText.style.marginTop = '-12px';
  } else if (compactMode) {
    msgText.innerHTML = `<span class=${message.color}>${message.author}</span><br>`;
    prevID = message.id;
  } else {
    msgText.innerHTML = `<span class=${message.color}>${message.author}</span>: `;
    prevID = message.id;
  }
  prevTime = compactTime;
  prevAuthor = message.author;
  msgText.className = 'msgtxt'
  let content = document.createElement('span')
  content.id = 'messageContent'
  content.className = 'messageData'
  content.innerHTML = message.content
  msgText.append(content)
  if (message.attachments && !lowBandwidth) {
    let imagediv = document.createElement('div');
    imagediv.className = 'imageAttachment'
    if (altCdn) {
      imagediv.innerHTML = message.attachments.replace('cdn', 'altcdn');
    } else {
      imagediv.innerHTML = message.attachments
    }
    if (message.attachments.includes('img') && !message.attachments.includes('video')) {
      imagediv.addEventListener('click', () => {
        let media = document.getElementById('fullMedia');
        media.style.display = 'flex';
        media.innerHTML = message.attachments.replace('imgAttachment', 'fullscreenImg').replace('thumbnail', 'img');
        media.addEventListener('click', () => {
          media.style.display = 'none';
        });
      });
    }
    msgText.append(imagediv)
  } else if (message.attachments && lowBandwidth) {
    let imagediv = document.createElement('div');
    imagediv.className = 'imageAttachment'
    imagediv.innerHTML = '<div class=imgAttachment><h2>Low bandwidth mode enabled</h2><br><p>Please disable low bandwidth mode to see images</p></div>'
    msgText.append(imagediv)
  }
  if (message.timestamp) {
    messagebox.addEventListener('mouseenter', () => {
      if (document.getElementById('timestampDiv')) {
        document.getElementById('timestampDiv').remove()
      }
      let tempTimestamp = message.timestamp
      let time = new Date(tempTimestamp).toLocaleString()
      let timestamp = document.createElement('div');
      timestamp.innerHTML = `<p id=timestampDivText>${time}</p>`
      timestamp.id = 'timestampDiv'
      messagebox.appendChild(timestamp)
    })
    messagebox.addEventListener('mouseleave', () => {
      document.getElementById('timestampDiv').remove()
    })
  }
  if (message.author == logusername || message.author == regusername) {
    messagebox.addEventListener('mouseenter', () => {
      if (document.getElementById('messageToolDiv')) {
        document.getElementById('messageToolDiv').remove()
      }
      let tools = document.createElement('div');
      tools.innerHTML = `<button id=editMessage>Edit</button><button id=deleteMessage>Delete</button>`
      tools.id = 'messageToolDiv'
      messagebox.appendChild(tools)
      document.getElementById('editMessage').addEventListener('click', () => {
        if (!document.getElementById('editInput')) {
          let messageText = message.content
          content.remove()
          let editInput = document.createElement('input')
          editInput.id = 'editInput'
          editInput.value = messageText
          editInput.addEventListener('keyup', (event) => {
            if (event.key === 'Enter') {
              socket.emit('editMessage', message.id, editInput.value)
            }
          })
          msgText.appendChild(editInput)
        }
      })
      document.getElementById('deleteMessage').addEventListener('click', () => {
        socket.emit('deleteMessage', message.id)
      })
    })
    messagebox.addEventListener('mouseleave', () => {
      document.getElementById('messageToolDiv').remove()
    })
  }
  messagebox.appendChild(msgText)
  container.appendChild(messagebox)
  container.scrollTop = container.scrollHeight;
  for (let func in distCallback['msgDist']) {
    window[distCallback['msgDist'][func]]({'content': message.content, 'attachments': message.attachments, 'element': messagebox, 'author': message.author});
  }
});

function removeTyping(username) {
  document.getElementById(`typing${username}`).remove()
}

socket.on("userTyping", (username) => {
  if (!document.getElementById(`typing${username}`) || username !== regusername || username !== logusername) {
    let typingDiv = document.createElement('div');
    let typingIndicator = document.createElement('p');
    typingDiv.id = `typing${username}`
    typingIndicator.innerText = `${username} is typing...`
    typingDiv.className = 'typingIndDiv'
    typingDiv.appendChild(typingIndicator)
    document.body.appendChild(typingDiv)
    setTimeout(removeTyping, 5000, username)
  }
})

socket.on("serverLoad", (load) => {
  if (true) {
    document.getElementById('progressDiv').remove()
  } else {
    let loadText = document.getElementById('load');
    progressBar.value = load;
    loadText.innerText = `Server load (${load}%):`
  }
})

socket.on("messageHistory", (messages) => {
  doneLoading = false;
  let container = document.getElementById('messageBox');
  container.innerHTML = ''
  for (let i = 0; i < messages.length; i++) {
    let messagebox = document.createElement('div')
    messagebox.className = 'msgbox'
    messagebox.id = `message${messages[i].id}`;
    let msgText = document.createElement('p')
    let compactTime = new Date(messages[i].timestamp += 'Z').getTime()
    if (compactTime < prevTime + 30000 && compactMode && messages[i].author == prevAuthor) {
      msgText.innerHTML = ``
      msgText.style.marginTop = '-12px';
    } else if (compactMode) {
      msgText.innerHTML = `<span class=${messages[i].color}>${messages[i].author}</span><br>`;
      prevID = messages[i].id;
    } else {
      msgText.innerHTML = `<span class=${messages[i].color}>${messages[i].author}</span>: `;
      prevID = messages[i].id;
    }
    prevTime = compactTime;
    prevAuthor = messages[i].author;
    msgText.className = 'msgtxt'
    let content = document.createElement('span')
    content.id = 'messageContent'
    content.className = 'messageData'
    content.innerHTML = messages[i].content
    msgText.append(content)
    if (messages[i].attachments && !lowBandwidth) {
      let imagediv = document.createElement('div');
      imagediv.className = 'imageAttachment'
      if (altCdn) {
        imagediv.innerHTML = messages[i].attachments.replace('cdn', 'altcdn');
      } else {
        imagediv.innerHTML = messages[i].attachments
      }
      if (messages[i].attachments.includes('img') && !messages[i].attachments.includes('video')) {
        imagediv.addEventListener('click', () => {
          let media = document.getElementById('fullMedia');
          media.style.display = 'flex';
          media.innerHTML = messages[i].attachments.replace('imgAttachment', 'fullscreenImg').replace('thumbnail', 'img');
          media.addEventListener('click', () => {
            media.style.display = 'none';
          });
        });
      }
      msgText.append(imagediv)
    } else if (messages[i].attachments && lowBandwidth) {
      let imagediv = document.createElement('div');
      imagediv.className = 'imageAttachment'
      imagediv.innerHTML = '<div class=imgAttachment><h2>Low bandwidth mode enabled</h2><br><p>Please disable low bandwidth mode to see images</p></div>'
      msgText.append(imagediv)
    }
    if (messages[i].timestamp) {
      messagebox.addEventListener('mouseenter', () => {
        if (document.getElementById('timestampDiv')) {
          document.getElementById('timestampDiv').remove()
        }
        let tempTimestamp = messages[i].timestamp
        let time = new Date(tempTimestamp).toLocaleString()
        let timestamp = document.createElement('div');
        timestamp.innerHTML = `<p id=timestampDivText>${time}</p>`
        timestamp.id = 'timestampDiv'
        messagebox.appendChild(timestamp)
      })
      messagebox.addEventListener('mouseleave', () => {
        document.getElementById('timestampDiv').remove()
      })
    }
    if (messages[i].author == logusername || messages[i].author == regusername || logusername == 'admin') {
      messagebox.addEventListener('mouseenter', () => {
        if (document.getElementById('messageToolDiv')) {
          document.getElementById('messageToolDiv').remove()
        }
        let tools = document.createElement('div');
        tools.innerHTML = `<button id=editMessage>Edit</button><button id=deleteMessage>Delete</button>`
        tools.id = 'messageToolDiv'
        messagebox.appendChild(tools)
        document.getElementById('editMessage').addEventListener('click', () => {
        if (!document.getElementById('editInput')) {
          let messageText = messages[i].content
          content.remove()
          let editInput = document.createElement('input')
          editInput.id = 'editInput'
          editInput.value = messageText
          editInput.addEventListener('keyup', (event) => {
            if (event.key === 'Enter') {
              socket.emit('editMessage', messages[i].id, editInput.value)
            }
          })
          msgText.appendChild(editInput)
        }
        });
        document.getElementById('deleteMessage').addEventListener('click', () => {
          socket.emit('deleteMessage', messages[i].id)
        })
      })
      messagebox.addEventListener('mouseleave', () => {
        document.getElementById('messageToolDiv').remove()
      })
    }
    messagebox.appendChild(msgText)
    container.appendChild(messagebox)
    for (let func in distCallback['msgDist']) {
      window[distCallback['msgDist'][func]]({'content': messages[i].content, 'attachments': messages[i].attachments, 'element': messagebox, 'author': messages[i].author});
    }
  }
  container.scrollTop = container.scrollHeight;
  doneLoading = true;
  for (let func in distCallback['history']) {
    window[distCallback['history'][func]]();
  }
})

socket.on("recieveRooms", (rooms) => {
  if (document.getElementsByClassName('roomListing')) {
    while (document.getElementsByClassName('roomListing').length > 0) {
      document.getElementsByClassName('roomListing')[0].remove();
    }
  }
  for (let room in rooms) {
    let roomText = document.createElement('div');
    if (rooms[room]['protected']) {
      roomText.innerHTML = `<p>${rooms[room]['name']}</p><svg class=lockIco xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M17,9V7A5,5,0,0,0,7,7V9a3,3,0,0,0-3,3v7a3,3,0,0,0,3,3H17a3,3,0,0,0,3-3V12A3,3,0,0,0,17,9ZM9,7a3,3,0,0,1,6,0V9H9Zm9,12a1,1,0,0,1-1,1H7a1,1,0,0,1-1-1V12a1,1,0,0,1,1-1H17a1,1,0,0,1,1,1Z"/></svg>`
      roomText.addEventListener('click', () => {
        document.getElementById('openRoomBrowser').click()
        document.getElementById('msginput').value = `/joinroom ${rooms[room]['name']} {pass}`
      })
    } else {
      roomText.innerHTML = `<p>${rooms[room]['name']}</p>`
      roomText.addEventListener('click', () => {
        document.getElementById('openRoomBrowser').click()
        document.getElementById('msginput').value = `/joinroom ${rooms[room]['name']}`
        sendMsg(document.getElementById('msginput').value)
        document.getElementById('msginput').value = ''
      })
    }
    roomText.className = 'roomListing'
    document.getElementById('roomBrowser').appendChild(roomText)
  }
})

socket.on("statusCallback", (error) => {
  if (error.error) {
    document.getElementById('errorText').innerHTML = `Error: ${error.error}\nDescription: ${error.description}`
    document.getElementById('errorBox').showModal()
  } else if (error.status) {
    if (error.status === 'accountCreated' || error.status === 'accountLogin') {
      document.getElementById('registerBox').close()
      document.getElementById('loginBox').close()
      document.getElementById('registerBtn').remove()
      document.getElementById('loginBtn').remove()
      document.getElementById('registerLoginDiv').remove()
      document.getElementById('blurFilter').remove()
      if (!localStorage.getItem('username') || !localStorage.getItem('password')) {
        localStorage.setItem('username', username)
        localStorage.setItem('password', password)
      }
      let settings = document.createElement('button')
      settings.id = 'settingsButton'
      settings.innerHTML = '<svg id=settingsIco xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><path d="M27.526 12.682a11.906 11.906 0 0 0-1.028-2.492l1.988-4.182a16.159 16.159 0 0 0-2.494-2.494L21.81 5.502a11.97 11.97 0 0 0-2.492-1.028L17.762.102C17.184.038 16.596 0 16 0s-1.184.038-1.762.102l-1.556 4.372c-.874.252-1.71.596-2.49 1.028L6.008 3.514a16.159 16.159 0 0 0-2.494 2.494l1.988 4.182a11.97 11.97 0 0 0-1.028 2.492L.102 14.238C.038 14.816 0 15.404 0 16s.038 1.184.102 1.762l4.374 1.556c.252.876.594 1.71 1.028 2.492l-1.988 4.182c.738.92 1.574 1.758 2.494 2.494l4.182-1.988c.78.432 1.616.776 2.492 1.028L14.24 31.9c.576.062 1.164.1 1.76.1s1.184-.038 1.762-.102l1.556-4.374c.876-.252 1.71-.594 2.492-1.028l4.182 1.988a16.071 16.071 0 0 0 2.494-2.494l-1.988-4.182a11.97 11.97 0 0 0 1.028-2.492L31.9 17.76c.062-.576.1-1.164.1-1.76s-.038-1.184-.102-1.762l-4.372-1.556zM16 24a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm-4-8a4 4 1080 1 0 8 0 4 4 1080 1 0-8 0z"/></svg>'
      settings.addEventListener('click', () => {
        document.getElementById('userSettings').showModal()
      })
      document.getElementById('inputDiv').prepend(settings)
      document.getElementById('msginput').addEventListener('keyup', () => {
        socket.emit('amTyping')
      })
      socket.emit('requestUpdate')
      socket.emit('has_2fa')
      if (localStorage.getItem('localVersion')) {
        socket.emit('versionNum', localStorage.getItem('localVersion'))
      } else {
        socket.emit('versionNum', 'getLatest')
      }
   }
  } else if (error.popup) {
    if (error.popup == 'passwordSuccess') {
      location.reload()
    }
    document.getElementById('statusText').innerHTML = `Status: ${error.popup}\nDescription: ${error.description}`
    document.getElementById('statusBox').showModal()
  } else if (error.changelog) {
    localStorage.setItem('localVersion', error.changelog)
    document.getElementById('changeText').innerHTML = `V${error.changelog}\n\n${error.description}`
    document.getElementById('changeBox').showModal()
  }
})

function spawnPopup() {
  if (document.getElementById('warning') != null) {
    document.getElementById('warning').remove()
    document.getElementById('code').remove()
  }
  if (parseInt(extData['ver'].replace('.', '')) < parseInt(localStorage.getItem('localVersion').replace('.', ''))) {
    document.getElementById('desc').innerHTML = `Warning! This theme/extension was created in version ${extData['ver']}. Your current client version is ${localStorage.getItem('localVersion')}. It may behave unexpectedly!`
  } else {
    document.getElementById('desc').innerHTML = ''
  }
  if (extData['id'] == 'omext') {
    let box = document.getElementById('extensionBox')
    let code = document.createElement('pre');
    code.innerHTML = extData['customJS']
    code.id = 'code';
    box.prepend(code);
    let warning = document.createElement('p');
    warning.innerHTML = 'Warning! Extensions have lots of power, and can leak account information. Please review the code below, and only install extensions you trust.';
    warning.id = 'warning';
    box.prepend(warning);
    hljs.highlightElement(code);
  }
  document.getElementById('title').innerHTML = `"${extData['name']}"`
  document.getElementById('extensionBox').showModal()
}

function chunkString(str, length) {
  return str.match(new RegExp('.{1,' + length + '}', 'g'));
}

socket.on('uploadKeyCallback', (uploadKey) => {
  currentUploadKey = uploadKey
  sendMsg(document.getElementById('msginput').value);
})

function sendMsg(msg) {
    if (document.getElementsByClassName('imgPreviewDiv').length >= 1 && currentUploadKey.length > 5) {
      let imagelement = document.getElementsByClassName('imgPreview')[0];
      let rawdata;
      if (currentData.length > 3) {
        rawdata = currentData;
      } else {
        rawdata = imagelement.src;
      }
      data = chunkString(rawdata, 50000);
      let progressbar = document.createElement('progress');
      progressbar.id = 'fileUploadProgress'
      progressbar.max = 1
      progressbar.value = 0
      document.body.appendChild(progressbar)
      let finalPart = data.length;
      let currentPart = 0;
      document.getElementById('msginput').disabled = true
      document.getElementById('send').disabled = true
      let uploadLoop = setInterval(() => {
        if (currentPart > finalPart) {
          clearInterval(uploadLoop)
          socket.emit('dataSend', {'part': 'transferComplete', 'id': currentUploadKey})
          socket.emit("recieve_msg", {'msg': msg, 'dataid': currentUploadKey})
          currentUploadKey = ''
          document.getElementById('msginput').value = ''
          document.getElementsByClassName('imgPreviewDiv')[0].remove()
          document.getElementById('msginput').disabled = false
          document.getElementById('send').disabled = false
          progressbar.remove()
          return
        }
        socket.emit('dataSend', {'part': data[currentPart], 'id': currentUploadKey})
        progressbar.value = (currentPart/data.length)
        currentPart++;
      }, 1)
      /*for (let part in data) {
        socket.emit('dataSend', {'part': data[part], 'id': currentUploadKey})
        progressbar.value = (part/data.length)*100
      }*/
    } else if (document.getElementsByClassName('imgPreviewDiv').length >= 1 && currentUploadKey.length < 3) {
      socket.emit('requestUploadKey');
      return
    } else {
      socket.emit("recieve_msg", {'msg': msg, 'dataid': false});
      document.getElementById('msginput').value = ''
    }
}

function setImageHeight() {
  if (document.getElementById('customImageSize')) {document.getElementById('customImageSize').remove()}
  let style = document.createElement('style');
  style.id = 'customImageSize';
  style.innerHTML = `
  .imgAttachment {
  height: ${document.getElementById('imageSize').value} !important;
  }
  `;
  document.head.appendChild(style);
}

function setCustomCss() {
  if (document.getElementById('userCss')) {document.getElementById('userCss').remove()}
  let style = document.createElement('style');
  style.id = 'userCss';
  style.innerHTML = document.getElementById('customCss').value;
  document.head.appendChild(style);
}

function setCustomJS() {
  if (document.getElementById('userJS')) {document.getElementById('userJS').remove()}
  let script = document.createElement('script');
  script.id = 'userJS';
  script.innerHTML = editor.getValue();
  document.head.appendChild(script);
}

function openFiles(inevent) {
  if (!document.getElementsByClassName('imgPreviewDiv').length == 0) {return}
    document.getElementById('messageBox').className = 'animateUp';
    let fileArray = Array.from(inevent.files)
    for(let i = 0; i < inevent.files.length; i++){
      fileId = document.getElementsByClassName('imgPreviewDiv').length + 1
      let imagePreviewDiv = document.createElement('div');
      imagePreviewDiv.className = 'imgPreviewDiv'
      imagePreviewDiv.id = `imgPreviewDiv${fileId}`
      let deleteButton = document.createElement('button');
      deleteButton.className = 'fileDeleteButton'
      deleteButton.addEventListener('click', () => {
        if ((document.getElementsByClassName('imgPreviewDiv').length - 1) < 1) {
          document.getElementById('messageBox').className = 'animateDown';
        }
        fileArray.splice(fileId, 1)
        imagePreviewDiv.remove()
      })
      deleteButton.innerHTML = '<svg class=fileDeleteIco xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g data-name="Layer 2"><path d="m13.41 12 4.3-4.29a1 1 0 1 0-1.42-1.42L12 10.59l-4.29-4.3a1 1 0 0 0-1.42 1.42l4.3 4.29-4.3 4.29a1 1 0 0 0 0 1.42 1 1 0 0 0 1.42 0l4.29-4.3 4.29 4.3a1 1 0 0 0 1.42 0 1 1 0 0 0 0-1.42z" data-name="close"/></g></svg>'
      imagePreviewDiv.appendChild(deleteButton);
      let fileName = document.getElementById('fileUpload').value;
      const reader = new FileReader();
      let imagePreview;
      reader.onload = (e) => {
        if (fileName.includes('omtheme') || fileName.includes('omext')) {
          imagePreview = document.createElement('p');
          imagePreview.innerHTML = fileName
          currentData = e.target.result;
          imagePreview.className = 'imgPreview'
          imagePreviewDiv.appendChild(imagePreview)
          document.body.appendChild(imagePreviewDiv)
        } else {
          imagePreview = document.createElement('img');
          imagePreview.src = e.target.result;
          imagePreview.className = 'imgPreview'
          imagePreviewDiv.appendChild(imagePreview)
          document.body.appendChild(imagePreviewDiv)
        }
      }
      if (fileName.includes('omtheme') || fileName.includes('omext')) { 
        reader.readAsText(fileArray[i]);
      } else {
        reader.readAsDataURL(fileArray[i]);
      }
    }
}

socket.on('twoKey', (data) => {
  if (data.status != 'success') {
    let text = document.getElementById('enterKey');
    text.innerHTML = '2FA key invalid.';
    text.style.color = 'red';
  } else {
    let dialog = document.getElementById('resetPass');
    dialog.innerHTML = '';
    let passInput = document.createElement('input');
    passInput.placeholder = 'New Password';
    passInput.id = 'passwordInput';
    dialog.appendChild(passInput);
    let accept = document.createElement('button');
    accept.id = 'acceptChange';
    accept.innerHTML = 'Change Password';
    accept.addEventListener('click', () => {
      localStorage.setItem('password', passInput.value);
      socket.emit('change_password', data.key, passInput.value);
    });
    dialog.appendChild(accept);
  }
})

function setCSSvar(name) {
  if (localStorage.getItem(name) !== null) {
    let color = localStorage.getItem(name);
    root.style.setProperty(`--${name}`, color);
    document.getElementById(`custom${name}Color`).value = color;
  }
}

function themeChange(value) {
  document.getElementById(`custom${value}Color`).addEventListener('change', () => {
    let color = document.getElementById(`custom${value}Color`).value;
    root.style.setProperty(`--${value}`, color);
    localStorage.setItem(value, color)
  });
}

function checkbox(boxVal) {
  if (localStorage.getItem(boxVal) !== null) {
    let checked = JSON.parse(localStorage.getItem(boxVal))
    lowBandwidth = checked;
    document.getElementById(`${boxVal}Check`).checked = checked;
  }
}

window.onload = function() {
  continueLoading = () => {
    let scriptEditor = document.createElement('script');
    scriptEditor.innerHTML = 'let editor = ace.edit("editor"); editor.setTheme("ace/theme/monokai"); editor.session.setMode("ace/mode/javascript");'
    document.getElementById('advBehavior').appendChild(scriptEditor);
    document.getElementById('accept2fa').addEventListener('click', () => {
      let key = document.getElementById('2faIn').value;
      socket.emit('validate_2fa', key);
    });
    document.getElementById('fullMedia').style.display = 'none';
    document.getElementById('compactCheck').checked = true;
    document.getElementById('custombackgroundColor').value = '#333333'
    document.getElementById('customhighlightColor').value = '#2C2C2C'
    document.getElementById('customaccentColor').value = '#D3D3D3'
    document.getElementById('exportId').value = "New Theme"
    document.getElementById('extId').value = "New Extension"
    if (localStorage.getItem('extensions') !== null) {
      let extensions = JSON.parse(localStorage.getItem('extensions'));
      for (let extension in extensions) {
        let extensionsDiv = document.getElementById('exts');
        let extensionDiv = document.createElement('div');
        extensionDiv.className = 'extDiv';
        let extensionName = document.createElement('p');
        extensionName.innerText = extensions[extension]['name'];
        extensionName.className = 'extensionName';
        let userJS = document.createElement('script');
        userJS.className = 'JSextension';
        userJS.innerHTML = extensions[extension]['customJS'];
        let removeButton = document.createElement('button');
        removeButton.className = 'extRemoveButton';
        removeButton.innerHTML = 'Delete'
        removeButton.addEventListener('click', () => {
          userJS.remove()
          extensionName.remove()
          extensionDiv.remove()
          let extensions = JSON.parse(localStorage.getItem('extensions'))
          extensions.pop(extension)
          localStorage.setItem('extensions', JSON.stringify(extensions))
          removeButton.remove()
        })
        document.head.appendChild(userJS);
        extensionDiv.append(extensionName);
        extensionDiv.append(removeButton);
        extensionsDiv.append(extensionDiv)
      }
    } else {
      localStorage.setItem('extensions', JSON.stringify([]))
    }
    if (localStorage.getItem('compact') !== null) {
      let state = JSON.parse(localStorage.getItem('compact'));
      compactMode = state;
      document.getElementById('compactCheck').checked = state;
    }
    setCSSvar('background');
    setCSSvar('highlight')
    setCSSvar('accent')
    themeChange('background')
    themeChange('highlight')
    themeChange('accent')
    if (localStorage.getItem('mediaHeight') !== null) {
      let mediaHeight = localStorage.getItem('mediaHeight');
      document.getElementById('imageSize').value = mediaHeight;
      setImageHeight();
    }
    if (localStorage.getItem('customCss') !== null) {
      let customCss = localStorage.getItem('customCss');
      document.getElementById('customCss').value = customCss;
      setCustomCss();
    }
    if (localStorage.getItem('customJS') !== null) {
      let customJS = localStorage.getItem('customJS');
      editor.setValue(customJS);
      setCustomJS();
    }
    checkbox('lowBandwidth')
    document.getElementById('saveSettings').addEventListener('click', () => {
      localStorage.setItem('mediaHeight', document.getElementById('imageSize').value);
      localStorage.setItem('customCss', document.getElementById('customCss').value);
      localStorage.setItem('customJS', editor.getValue());
      setImageHeight();
      setCustomCss();
      setCustomJS();
    })
    document.getElementById('importTheme').addEventListener('click', () => {
      document.getElementById('uploadCustom').click();
    })
    document.getElementById('importExtension').addEventListener('click', () => {
      document.getElementById('uploadCustom').click();
    })
    document.getElementById('uploadCustom').addEventListener('change', (event) => {
      const reader = new FileReader();
        reader.onload = (e) => {
          extData = JSON.parse(e.target.result);
          spawnPopup()
        }
      reader.readAsText(event.target.files[0]);
    });
    document.getElementById('confirmLoad').addEventListener('click', () => {
      if (extData['id'] == 'omtheme') {
        localStorage.setItem('background', extData['background'] || '#333')
        localStorage.setItem('accent', extData['accent'] || '#D3D3D3')
        localStorage.setItem('highlight', extData['highlight'] || '#2C2C2C')
        localStorage.setItem('customCss', extData['css'] || '')
        window.location.reload()
      } else if (extData['id'] == 'omext') {
        let extensions = JSON.parse(localStorage.getItem('extensions'))
        extensions.push(extData)
        localStorage.setItem('extensions', JSON.stringify(extensions))
        window.location.reload()
      }
    })
    document.getElementById('exportTheme').addEventListener('click', () => {
      let themeFile =
      {'id': 'omtheme',
      'name': document.getElementById('exportId').value,
      'ver': localStorage.getItem('localVersion') || '1.0.0',
      'background': localStorage.getItem('background') || '#333',
      'highlight': localStorage.getItem('highlight') || '#2C2C2C',
      'accent': localStorage.getItem('accent') || '#D3D3D3',
      'css': localStorage.getItem('customCss') || false}
      download(`${document.getElementById('exportId').value}.omtheme`, themeFile)
    });
    document.getElementById('exportExtension').addEventListener('click', () => {
      let extensionFile = {'id': 'omext',
      'name': document.getElementById('extId').value,
      'ver': localStorage.getItem('localVersion') || '1.0.0',
      'description': document.getElementById('extDesc').value,
      'customJS': editor.getValue()}
      download(`${document.getElementById('extId').value}.omext`, extensionFile)
    });
    document.getElementById('lowBandwidthCheck').addEventListener('change', () => {
      let checked = document.getElementById('bandCheck').checked;
      lowBandwidth = checked;
      localStorage.setItem('lowBandwidth', JSON.stringify(checked));
      socket.emit('requestUpdate');
    })
    document.getElementById('compactCheck').addEventListener('change', () => {
      let checked = document.getElementById('compactCheck').checked;
      compactMode = checked;
      localStorage.setItem('compact', JSON.stringify(checked));
      socket.emit('requestUpdate');
    });
    document.getElementById('openRoomBrowser').addEventListener('click', () => {
      let roomBrowser = document.getElementById('roomBrowser');
      let bMobile = navigator.userAgent.indexOf( "iPhone" ) !== -1 || navigator.userAgent.indexOf( "Android" ) !== -1 || navigator.userAgent.indexOf( "Windows Phone" ) !== -1 ;
      if (bMobile) {
        roomBrowser.style.width = '99vw'
        document.getElementById('titleBreak').style.width = '99vw'
      }
      if (roomBrowser.className == 'close' || roomBrowser.className == 'load') {
        roomBrowser.className = 'open';
      } else {
        roomBrowser.className = 'close';
      }
    })
    document.getElementById('fileUpload').addEventListener('change', (event) => {
      openFiles(event.target);
    });
    document.getElementById('fileClick').addEventListener('click', () => {
      document.getElementById('fileUpload').click()
    });
    if (localStorage.getItem('username') && localStorage.getItem('password')) {
      socket.emit("login", localStorage.getItem('username'), localStorage.getItem('password'))
      logusername = localStorage.getItem('username')
    }
      document.querySelector('#send').addEventListener('click', () => {
        let input = document.getElementById('msginput')
        sendMsg(input.value)
      });
      document.getElementById('registerBtn').addEventListener('click', () => {
        document.getElementById('registerBox').showModal()
      });
      document.getElementById('loginBtn').addEventListener('click', () => {
        document.getElementById('loginBox').showModal()
      })
      document.getElementById('register').addEventListener('click', () => {
        regusername = document.getElementById('username').value;
        let regpassword = document.getElementById('password').value;
        username = regusername
        password = regpassword
        socket.emit("register_account", regusername, regpassword)
      });
      document.getElementById('login').addEventListener('click', () => {
        logusername = document.getElementById('logusername').value;
        let logpassword = document.getElementById('logpassword').value;
        username = logusername
        password = logpassword
        socket.emit("login", logusername, logpassword)
      })
      document.getElementById('password').addEventListener('keyup', (event) => {
        if (event.code === 'Enter') {
          regusername = document.getElementById('username').value;
          let regpassword = document.getElementById('password').value;
          username = regusername
          password = regpassword
          socket.emit("register_account", regusername, regpassword)
        }
      })
      document.getElementById('logpassword').addEventListener('keyup', (event) => {
        if (event.code === 'Enter') {
          logusername = document.getElementById('logusername').value;
          let logpassword = document.getElementById('logpassword').value;
          username = logusername
          password = logpassword
          socket.emit("login", logusername, logpassword)
        }
      })
      document.getElementById('msginput').addEventListener('keyup', (event) => {
        if (event.code === 'Enter' && !event.shiftKey) {
          let input = document.getElementById('msginput')
          sendMsg(input.value)
        }
      })
      document.getElementById('msginput').addEventListener('paste', (event) => {
        if (event.clipboardData.files.length > 0) {
          openFiles(event.clipboardData);
        }
      })
    }
  HTMLDivElement.prototype.close = function() {this.style.display = 'none'};
  HTMLDivElement.prototype.showModal = function() {this.style.display = 'block'};
  continueLoading();
}