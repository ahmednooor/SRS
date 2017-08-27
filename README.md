# Student Record System

> A basic student record system.

[Screenshots](https://github.com/ahmednooor/SRS/tree/master/screenshots)

![Screenshot](https://raw.githubusercontent.com/ahmednooor/SRS/master/screenshots/1.png)

> Tech Stack: Python(Flask), SQLite, HTML, CSS(Bootstrap), Javascript(JQuery).

## Features
* Student's personal record.
* Student card generation.
* Student's test record.
* Student's fee record.
* Fee receipt generation.
* Ability to change institution name and logo from within the app.
* Create/Delete Administrators from root account.
* Admin can only 1) create/edit a student, 2) create test and fee records, 3) edit personal profile of itself.
* Root has all privileges like 1) create/edit/delete students/admins/test records/fee records, 2) edit institution name and logo.

## Default Username and Password
> Root User:
`Username:` root
`Password:` root

> Admin User:
`Username:` admin
`Password:` admin

### Installation
> You will need to have python 3.x installed. 3.6 recommended.

Open terminal and go to the project directory and type following to install dependencies
```sh
pip install -r requirements.txt
```
Type the following command to run the app
```sh
python app.py
```

### Creating an executable for windows using cx_Freeze
> You will need to have `cx_Freeze` installed first
```sh
pip install cx_Freeze
```
Type following to generate the executable
```sh
python setup.py build
```
> NOTE: You can change the `setup.py` file to generate the executable with your own instution's name. Just replace `Institution_Name` with your institution's name.
You can also replace the three default logo files at `/static/img/system/[logo.png, logo.jpg, logo.ico]` with your own institution's logo files. 

## Contributions/Issues/Feedback
> Contributions to this project directly is not recommended. Feel free to fork it and modify according to your needs.
Feel free too post any issues/feedback in the issues section.

## Licence and Credits

License: [MIT](https://opensource.org/licenses/MIT)

Author:  [Ahmed Noor](https://github.com/ahmednooor)

Credits: [FlatIcon](http://flaticon.com/) for default logo. [FontAwesome](http://fontawesome.io/) for UI icons.
