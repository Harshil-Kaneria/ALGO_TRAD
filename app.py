def fileLoad(name):
    with open(name, 'r') as file:
        exec(file.read(), globals())  

fileLoad('app/imports.py')

app = Flask(__name__)
CORS(app)
load_dotenv()

files_to_load = [
    'app/globalVariables.py',
    'app/dataLogin.py',
    'app/classAI.py',
    'app/functions.py',
    'app/apis.py'
]
for filename in files_to_load:
    fileLoad(filename)

if __name__ == '__main__':
    fileLoad('app/serverLoad.py')