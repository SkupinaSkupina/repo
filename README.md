# **Navodila za uporabo GIT:**
## Inicializacija GIT:
`git init`

## Sync main branch z local branch:
`git pull https://github.com/SkupinaSkupina/repo.git`

## Nastavi origin:
`git remote add origin https://github.com/SkupinaSkupina/repo.git`

## Ustvari novi branch z imenom:
`git checkout -b <new branch name>`

## Spremeni branch
`git checkout <branch name>`

## Preveri za nove spremembe:
`git status`

## Dodaj nove spremembe v commit:
`git add .`
ali
`git add <ime_datoteke>`

## Commit-u dodaj ime:
`git commit -m "Your commit message"`
oz.
`git commit -m "SKP-XX <Your commit message>"`

## Push-aj commit na branch-name
`git push <origin> <branch name>`

# **Navodila za uporabo prototipa aplikacije:**
  Najprej si nalozi vse knjiznice za python interpreter:  
    `pip install -r requirements.txt`
  Nato lahko zazenes main.py  
    cmd: `py main.py`
    lahko zaženeš tudi preko IDE