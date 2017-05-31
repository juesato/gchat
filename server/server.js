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
            console.log('emitted');
        } else {
            console.log('failure');
            socket.emit('login_auth', false);
        }
    });
  });
  setInterval(function() { 
    if (username) {
        var user = userCollection.find({username: username})
        user.each(function(err, doc) {
            if(err)
                throw err;
            if(doc==null)
                return;
            console.log(doc.contacts);
            socket.emit('contacts', doc.contacts);
        });
        // socket.emit('contacts', 'some stuff');
    }
  }, 5000);
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
    console.log('key', k);
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
                    timestamp: time.getHours() + ":" + time.getMinutes() + ":" + time.getSeconds() 
                }
            }
        });
        console.log('got msg', msg, err, res);
    });
    if (recip in user_to_socket) {
        sendHistory({username: recip, recip: sender});
    }
  });
  function sendHistory(data) {
    var sender = data['username'];
    var recip = data['recip'];
    var names = alpha(sender, recip);
    var name1 = names[0];
    var name2 = names[1];
    chatCollection.find({'participants': [name1, name2]}).toArray(function(err, results) {
        if (!results.length) return;
        console.log('len', results.length);
        socket.emit('history', {
            recip: recip,
            log: results[0].log
        });
    });
  }
  socket.on('history', sendHistory);
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
});

app.listen(8000);
/* server started */
console.log('> hello world running on port 8000');  