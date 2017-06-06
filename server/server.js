/*
Data Schema

Users: [(id, username, pw, email, avail, statusmsg, [Contacts])]
Chats: [(id, [users], [msgs])]

Contact = (username, relation)
*/


/* Idk how to do enums in JS */
// Availability
var OFFLINE = 'offline';
var ONLINE = 'online';

// Relationship
var FRIENDS = 'friends'
var REQUESTED = 'requested'
var PENDING = 'pending'


var util = require('util'),  
    http = require('http');

var fs = require('fs');

var exec = require('child_process').exec;

var MongoClient = require('mongodb').MongoClient
var userCollection;
var chatCollection;
MongoClient.connect('mongodb://127.0.0.1:27017/gchat', function(err, db) {
if(err) throw err;
userCollection = db.collection('users');
chatCollection = db.collection('chats');
// chatCollection = db.collection('chats');

// db.collection('users').findAndModify(
//   {username: 'guest'}, // query
//   [['_id','asc']],  // sort order
//   {$set: {contacts: [{'username':'juesato', 'relation':FRIENDS}]}}, // replacement, replaces only the field "hi"
//   {}, // options
//   function(err, object) {}
//   );
});

var app = http.createServer(function (req, res) {  
  res.writeHead(200, {'Content-Type': 'text/plain'});
  res.write("please don't look at this");
  res.end();
})

// var app = http.createServer()

var io = require('socket.io')(app);

function alpha(name1, name2) {
    if (name1 < name2) {
        return [name1, name2];
    } else {
        return [name2, name1];
    }
}

var user_to_socket = {}

io.on('connection', function(socket) {
  console.log("CONNECTION!");
  var username = false;
  socket.on('login', function(data) {
    var d = JSON.parse(data);
    var user = d['username'];
    var pass = d['password'];
    userCollection.find({username:user, password:pass}).toArray(function(err, results){
        if (results.length) {
            console.log('success');
            userCollection.update({username: user}, {
                $set: {
                    availability: ONLINE
                }
            });
            username = user;
            user_to_socket[user] = socket
            socket.emit('login_auth', true);
            socket.emit('my_status', results[0].status)
            sendContacts();
        } else {
            console.log('failure');
            socket.emit('login_auth', false);
        }
    });
  });
  socket.on('friend_request', function(data) {
    var sort = { 'username': -1 };
    userCollection.findAndModify({username: {$eq: data}}, sort, {
        $addToSet: {
            contacts: {
                username: username,
                relation: FRIENDS
            }
        }
    },
    function(err, doc) {
        // if it worked and the other username exists, add it
        // console.log('cb', err, doc);
        if (err) return;
        if (!doc || !doc.value || !doc.value.username) return;
        userCollection.findAndModify({username: {$eq: username}}, sort, {
            $addToSet: {
                contacts: {
                    username: data,
                    relation: FRIENDS
                }
            }
        });
    });
  });
  function sendContacts() { 
    if (username) {
        var user = userCollection.find({username: username})
        user.each(function(err, doc) {
            if (err) throw err;
            if (doc == null) return;
            socket.emit('contacts', doc.contacts);
        });
        // socket.emit('contacts', 'some stuff');
    }
  }
  setInterval(sendContacts, 5000);
  socket.on('friend', function(data) {
    var user = data;
    userCollection.find({username: user}).toArray(function(err, results) {
        socket.emit('friend_status', {
            username: user,
            status: results[0].status,
            avail: results[0].availability
        });
    });
  });
  socket.on('msg', function(data) {
    time = new Date();
    console.log('got message!' + data);
    var sender = data['username'];
    var recip  = data['receiver'];    
    var msg = data['msg'];
    var names = alpha(sender, recip);
    var name1 = names[0];
    var name2 = names[1];
    var k = name1 + name2;
    chatCollection.findAndModify(
        {'participants': [name1, name2]}, [],
        {$setOnInsert: {log: []}},
        {
            new: true,    // return new doc if one is upserted
            upsert: true
        } // insert the document if it does not exist
    , function(err, res) {
        chatCollection.update({'participants': [name1, name2]}, {
            $push: {
                log : {
                    sender: sender,
                    recip: recip,
                    msg: msg,
                    timestamp: time,
                    timestr: time.getHours() + ":" + time.getMinutes() + ":" + time.getSeconds() 
                }
            }
        },
        function() {
            if (recip in user_to_socket) {
                console.log('send to receiver', recip, sender);
                historyCb(user_to_socket[recip])({username: recip, recip: sender});
            }
        });
    });
  });
  function historyCb(socket) {
    return function(data) {
        var sender = data['username'];
        var recip = data['recip'];
        var names = alpha(sender, recip);
        var name1 = names[0];
        var name2 = names[1];
        chatCollection.find({'participants': [name1, name2]}).toArray(function(err, results) {
            if (!results.length) return;
            console.log('send history', results.length, name1, name2);
            socket.emit('history', {
                recip: recip,
                log: results[0].log
            });
        });
    }
  }
  socket.on('history', historyCb(socket));
  socket.on('disconnect', function() {
    console.log('Got disconnect!');
    userCollection.find({username:username}).toArray(function(err, results){
        userCollection.update({username: username}, {
            $set: {
                availability: OFFLINE
            }
        });
        delete user_to_socket[username];
    });
  });
    socket.on('status_update', function(data) {
        console.log('update status for ' + username + ' to ' + data);
        userCollection.update({username: username}, {
            $set: {
                status: data
            }
        });
    });
    socket.on('email_confirmation', function(data) {
        var email = data['email'];
        var key = data['key'];
        var cmd = 'echo "' + key + '" | mail -s "Your account confirmation code" ' + email;
        console.log('email_confirmation');
        console.log(cmd);
        exec(cmd, function(error, stdout, stderr) {});
    });
    socket.on('new_account', function(data) {
        var is_unique = true;
        userCollection.find({username: data['username']}).toArray(function(err, results) {
            if (results.length > 0) {
                console.log('not unique');
                return;
            }
            userCollection.insert({
                username: data['username'],
                password: data['password'],
                email: data['email'],
                availability: OFFLINE,
                status: '',
                contacts: []
            }, function(err, doc) {
                if (err) console.log('error');
                console.log('new account!'); 
            });
        });
    })
});

function sendEmail(username, body, subj) {
    var fname = 'tmp' + Math.floor(Math.random() * 100000).toString() + '.txt';
    console.log('sendEmail', username, body, subj);
    userCollection.find({username: username}).toArray(function(err, res) {
        if (res.length == 0) return;
        var email = res[0]['email'];
        fs.writeFile(fname, body, function(err) {
            if (err) return console.log(err);
            var cmd = 'cat ' + fname + ' | mail -s "' + subj + '" ' + email;
            console.log('sending email');
            console.log(cmd);
            exec(cmd, function(error, stdout, stderr) {
                fs.stat(fname, function (err, stats) {
                    if (err) return console.log(err);
                    fs.unlink(fname ,function(err) {
                        if(err) return console.log(err);
                        console.log('file deleted successfully');
                    });
                });
            });
        });
    });
}

function emailAndClearLogs() {
    var cursor = chatCollection.find({})
    cursor.each(function(err, doc) {
        if (err) throw err;
        if (!doc) return; // really unclear why i have to do this
        if (!('participants' in doc)) {
            console.log('broken entry', doc);
            return;
        }
        var participants = doc['participants'];
        var name1 = participants[0];
        var name2 = participants[1];
        var l = doc['log'].length;
        // var five_mins = 5 * 60 * 1000;
        var five_mins = 5 * 60 * 1000 * 0.02;
        var now = new Date();
        if (now - doc['log'][l-1]['timestamp'] > five_mins) {
            console.log('chat finished');
            // clear and email
            var email_body = ''
            for (i = 0; i < l; i++) {
                var sender = doc['log'][i]['sender'];
                var msg = doc['log'][i]['msg'];
                var timestr = doc['log'][i]['timestr'];
                email_body += sender + ' (' +  timestr + '): ' + msg + '\n';
            }
            email_body = email_body.replace('\\', '\\\\'); // escape backslashes
            email_body = email_body.replace('"', '\\"');
            sendEmail(name1, email_body, 'Chat with ' + name2 + ' (' + l.toString() + ' lines)')
            sendEmail(name2, email_body, 'Chat with ' + name1 + ' (' + l.toString() + ' lines)')

            // delete log
            chatCollection.remove({participants: participants},
                function(err, object) {
                    if(err) throw err;
                    console.log("document deleted", participants);
                }
            );
        }
    });
}

setInterval(emailAndClearLogs, 0.02 * 5*60*1000);
// setInterval(emailAndClearLogs, 5*60*1000);

app.listen(8000);
/* server started */
console.log('> hello world running on port 8000');  