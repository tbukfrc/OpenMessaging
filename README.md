# About

Hello! This is my latest project, OpenMessage. It's an open-source messenger written in Python (server) and JavaScript (browser). A CLI client is in the works.

I created this project to be as simple as possible to set up and use. Sending and recieving messages is handled via socket-io.

### Features:
* Instantly send and recieve messages
* Upload videos and images
* Create custom JS and CSS extensions and share them in chat
* Simple server config file
* Users can create a customizable amount of "rooms" (think discord channels), which can be locked with a password.

### Upcoming Features:
* Opt-In global auth system
* Plugin and theme repo
* User-hostable server proxy (to help people who can't port forward)
* Opt-In server discovery via server browser on main site

# How to install:

### Prerequisites:
* The following instructions assume you're using Debian Linux, though it should be easy to adapt to other OSes.
* The last step of the tutorial also assumes you have a domain, and a basic understanding of port forwarding and DNS. If you don't, there are plenty of tutorials on how to create DNS entries (specifically A records, if you're wondering), and port forward your server. That's not what this is meant to be.
* This also assumes that if you are in fact, using Debian, you have a basic understanding of the terminal, which you should if you're using Debian.


### First, clone the repo to whatever folder you want:  
`git clone https://github.com/tbukfrc/OpenMessaging && cd OpenMessaging`

### Next, install the dependencies for the server:  
`cd server && pip install -r requirements.txt`

### Then, install Redis (required):  
[https://redis.io/docs/getting-started/installation/](https://redis.io/docs/getting-started/installation/)

### Then, set up your config (see below example):  
```js
{
    // People with the below usernames have Admin privileges.
    "admins": [
        "admin",
        "example"
    ],
    // The port the server should listen on
    "server_port": 8010,
    // The port your Redis DB is on (a fresh install should be the default of 6379, if you have multiple instances make sure to change this to a new one)
    "redis_port": 6379,
    // The db within the defined Redis instance (if other services are using Redis, I would highly recommend creating a new instance, but changing this would work too)
    "redis_db": 0,
    // The domain of your CDN.
    "cdn_domain": "cdn.tbuk.me",
    // The file size limit of admin users (in MB)
    "admin_upload_limit": 100,
    // The file size limit of standard users (in MB)
    "user_upload_limit": 50,
    // The message character limit for all users
    "character_limit": 2000
}
```
### Finally, host the static web files and reverse proxy the server:  

This step is the most complicated. I recommend using Caddy for this, as it is very simple to use, and will automate getting SSL certificates for your server.
If you use something else (like Nginx), you should already know what to do, but if you don't, base your config off of the one below.

#### NOTE: If you don't have a domain, for whatever reason that may be, skip the following steps and direct connect.

First, you want to install Caddy. Follow their docs for whatever OS you're using. The below steps assume you're not using Docker, but you should still be able to follow it if you are.
[https://caddyserver.com/docs/install](https://caddyserver.com/docs/install)

Next, you want to modify the Caddyfile. You can either use a local Caddyfile, or the global one. I'll be using the global one.  
On Debian-based systems, this is located at `/etc/caddy/Caddyfile`  
This config will tell Caddy how to handle incoming requests  
Here is an example of the most basic config possible:
```py
backend.example.site {
  reverse_proxy 127.0.0.1:SERVER_PORT
}

messenger.example.site {
  root * /path/to/the/client_folder
	file_server
}

cdn.example.site {
  # (note: the CDN folder is a folder titled "cdn" in the root directory/the folder containing the client and server folders).
  root * /path/to/the/cdn_folder
  file_server
}
```
Make sure to change the paths and add the server port!

Once you've changed the config, run `sudo systemctl reload caddy`, and after a few seconds you should have a working instance of OpenMessaging with TLS/SSL!
