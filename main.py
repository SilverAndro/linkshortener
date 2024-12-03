import json
import boto3
from os import environ
from base64 import b64decode

s3 = boto3.client('s3')
response = s3.get_object(Bucket="linkshortener-store", Key="links.txt")
rawmapping = json.loads(response['Body'].read().decode('utf-8'))

username = environ["USERNAME"]
password = environ["PASSWORD"]

def redirection(path):
    if (path in rawmapping):
            destination = rawmapping[path]
            return {
                'statusCode': 301,
                'headers': {"Location": destination}
            }
    else:
        return {
            'statusCode': 404,
            'body': "Nothing here"
        }
        
def find_header(headers, key):
    for index in headers:
        if key.lower() == index.lower():
            return index
    return None

def request_auth():
    return {
            'statusCode': 401,
            'headers': {"WWW-Authenticate": "Basic"}
        }

def auth_valid(authHeader):
    splice = authHeader.split(" ")
    print(splice)
    if (not splice[0] == "Basic"):
        return False
    chunk = b64decode(splice[1].encode('ascii')).decode('ascii')
    creds = chunk.split(":")
    return creds[0] == username and creds[1] == password

def construct_dashboard():
    result = '''<!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <title>Link Shortener Dashboard</title>
        <link href="https://kizuati.com/favicon.ico" rel="icon" type="image/x-icon">
      </head>
      <body>
    	<script>
    	function getRandom() {
            var letters = "0123456789abcdef";
            var color = "";
            for (i = 0; i < 7; i++) {
                color += letters[Math.floor(Math.random() * 16)];
            }
            return color;
        }
        
        function copy(slug) {
            navigator.clipboard.writeText("https://s.kizuati.com/" + slug);
            alert("copied " + "https://s.kizuati.com/" + slug);
        }
        
        function del(slug) {
            fetch("https://s.kizuati.com/" + slug, {
              method: "DELETE"
            }).then((r) => document.getElementById(slug).remove());
        }
        
        function create() {
            slug = document.getElementById("slug").value;
            target = document.getElementById("target").value;
            if (!slug) {
                slug = getRandom();
            }
        
            if (target && document.getElementById("target").checkValidity() && document.getElementById("slug").checkValidity()) {
                console.log(slug);
                console.log(target);
                fetch("https://s.kizuati.com/" + slug + "?t=" + target, {
                  method: "PUT"
                }).then((r) => {
                    document.getElementById("slug").value = "";
                    document.getElementById("target").value = "";
                })
            }
        }
    	</script>
    	<div>
    		<input type="text" id="slug" name="slug" minlength="3" maxlength="22" size="24" placeholder="slug (leave blank for random)"/>
    		<input type="url" id="target" name="target" size="30" placeholder="target url"/>
    		<input type="button" value="create" onclick="create();"/>
    	</div>
    	<ul>
    '''
    
    for k, v in rawmapping.items():
        result += f"    		<li id=\"{k}\">{k} - {v} <input type=\"button\" value=\"copy\" onclick=\"copy('{k}');\"/> <input type=\"button\" value=\"delete\" onclick=\"del('{k}');\"/></li>"
        result += '\n'

    return result + '''
        	</ul>
      </body>
    </html>
    '''

def dashboard(event, requestContext):
    return {
            'statusCode': 200,
            'body': construct_dashboard(),
            'headers': {"Content-Type": "text/html; charset=utf-8"}
        }
        
def create(slug, target):
    rawmapping[slug] = target
    s3.put_object(Body=json.dumps(rawmapping), Bucket="linkshortener-store", Key="links.txt")
    return {
            'statusCode': 201,
            'body': "Ok"
        }
        
def delete(slug):
    rawmapping.pop(slug, None)
    s3.put_object(Body=json.dumps(rawmapping), Bucket="linkshortener-store", Key="links.txt")
    return {'statusCode': 204}

def lambda_handler(event, context):
    requestContext = event["requestContext"]
    path = event["rawPath"].replace(requestContext["stage"], "").replace("/", "")
    headers = event["headers"]
    method = requestContext["http"]["method"]
    query = event["rawQueryString"]
    hKey = find_header(headers, "Authorization")

    
    if method == "DELETE":
        if not hKey or not auth_valid(headers[hKey]):
            return request_auth()
        else:
            return delete(path)
    
    if method == "PUT":
        if not hKey or not auth_valid(headers[hKey]):
            return request_auth()
        else:
            return create(path, query.replace("t=", ""))
    
    if (path != ""):
        print("redirecting " + path)
        return redirection(path)
        
    if not hKey or not auth_valid(headers[hKey]):
        print("requesting auth")
        return request_auth()

    return dashboard(event, requestContext)
    
