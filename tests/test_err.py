import json
import ast

try:
    with open('error.txt', 'r') as f:
        text = f.read()
    
    # Text looks like: {"error":"{'message': '...', 'details': None, ...}"}
    d1 = json.loads(text)
    
    # d1["error"] is a string of a python dict due to Supabase throwing exceptions 
    err_str = d1["error"]
    
    d2 = ast.literal_eval(err_str)
    print("EXTRACTED ERROR:", d2.get("message"))
except Exception as e:
    print("Could not extract:", text)
