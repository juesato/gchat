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
            username = user;
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
  // socket.on('message', function(data) {
  //   console.log('got message!' + data);
  //   socket.emit('response', 'hello ' + data);
  // });
  // socket.on('emit', function() {
  //   socket.emit('emit_response');
  // });
});

app.listen(8000);
/* server started */
console.log('> hello world running on port 8000');  