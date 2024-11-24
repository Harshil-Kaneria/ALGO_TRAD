def fileLoad(name):
    with open(name, 'r') as file:
        exec(file.read(), globals())  

files_to_load = [
    'app/imports.py',
    'app/globalVariables.py',
    'app/databaseModel.py',
    'app/dataLogin.py',
    'app/classAI.py',
    'app/functions.py',
    'app/apis.py'
]
for filename in files_to_load:
    fileLoad(filename)

if __name__ == '__main__':
    fileLoad('app/serverLoad.py')