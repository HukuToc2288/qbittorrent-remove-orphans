#!/usr/bin/python3
import os
import sys

import requests
import json

# config

torrentsRoots = {"/пути/до/рабочих/директорий","C:/Users/Денис Попов"}

# webUI URL
webUiUrl = 'http://127.0.0.1:8113'
# webUI credentials
# WARNING: CLEARTEXT PASSWORD
# Make sure that the file is unreadable for others that torrent user
data = {
    'username': 'admin',
    'password': 'adminadmin'
}

# Login method
login_url = webUiUrl + '/api/v2/auth/login'
# Torrent list
torrentListUrl = webUiUrl + '/api/v2/torrents/info'
# Torrent content
torrentContentUrl = webUiUrl + '/api/v2/torrents/files'

headers = {
    'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/78.0.3904.70 Safari/537.36 '
}

def_headers = {
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/78.0.3904.70 Safari/537.36 '
}

simulate = True
cookieJar = None
filesToKeep = {}


def addTorrentToKeep(dataPath: str, torrentContent):
    # Оказывается, дерево жрёт ещё больше памяти, так что храним в простом списке
    for key in filesToKeep.keys():
        if dataPath.startswith(key):
            relativeDataPath = dataPath[len(key):]
            for contentItem in torrentContent:
                filesToKeep[key].append(os.path.normpath(os.path.join(relativeDataPath, contentItem['name'])))
            return True
    return False


def getAllTorrents():
    return json.loads(str(requests.get(torrentListUrl, headers=headers, cookies=cookieJar).content, 'utf-8'))


def getTorrentContents(torrentContent):
    params = {'hash': torrentContent}
    responseString = str(requests.get(torrentContentUrl, headers=headers, cookies=cookieJar, params=params).content,
                         'utf-8')
    try:
        responseJson = json.loads(responseString)
        return responseJson
    except Exception:
        print(responseString)
        raise Exception


def printProcessedCount(processed, total):
    print(f'Обработано {processed} из {total} раздач')


def checkFilesRecursive(torrentRoot: str):
    for subdir, dirs, files in os.walk(torrentRoot):
        for file in files:
            fullPath = os.path.join(subdir, file)
            pathToTest = fullPath[len(torrentRoot):]
            if pathToTest not in filesToKeep[torrentRoot]:
                if simulate:
                    print(f"Файл {fullPath} был бы удалён!")
                else:
                    os.remove(fullPath)
                    print(f"Файл {fullPath} удалён!")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


if __name__ == '__main__':
    print('Для очистки указаны каталоги:')
    for root in torrentsRoots:
        print('\t' + root)
    print(f'И торрент клиент с адресом:')
    print('\t' + webUiUrl)
    print('Все файлы в указанных каталогах, которые не относятся к данному торрент-клиенту, будут удалены!')
    print('Если данные неверны, остановите скрипт, и задайте нужные настройки')
    print('Не прописывайте каталоги, с которыми работают несколько торрент-клиентов!')
    print()
    print('Данный скрипт удаляет файлы навсгда (совсем навсегда!). Если вы с этим согласны, введите "yes"')
    print('Если вы просто хотите посмотреть, какие файлы были бы удалены, введите "dry"')
    print('Вводя "yes", вы соглашаетесь с тем, что не будете иметь претензий к автору скрипта в случае, '
          'если что-то пойдёт не так')
    print('Настоятельно рекомендую при первом запуске всё-таки ввести "dry"')
    print('Выйти отсюда можно, нажав Enter или Ctrl-C')
    print()
    print('fixme: Работа с путями Windows не тестирована, так что если вы пользователь этой ОС, '
          'вдвойне настоятельно рекомендую сначала ввести "dry"')
    print('fixme: Пустые директории пока не удалятся, вам придётся подчистить их чем-то другим')
    print()

    answer = input('Удаляем? ')
    if answer == 'yes':
        simulate = False
    elif answer == 'dry':
        simulate = True
    else:
        print("Выход")
        exit(0)

    print('Авторизация...')
    response = requests.post(login_url, data, headers=headers)

    # login error
    if response.text != 'Ok.':
        exit(0)

    cookieJar = response.cookies

    # get ALL torrents
    print('Запрос списка торрентов...')
    torrents = getAllTorrents()
    print(f'Сканирование {len(torrents)} раздач...')
    totalCount = len(torrents)
    if totalCount > 50000:
        print('Это может занять НЕПРИЛИЧНО много времени')
    elif totalCount > 10000:
        print('Это может занять много времени')
    elif totalCount > 1000:
        print('Это может занять некоторое время')
    processedCount = 0

    for root in torrentsRoots:
        filesToKeep[root] = []

    for torrent in torrents:
        dataPath = torrent['save_path']
        torrentHash = torrent['hash']
        torrentContent = getTorrentContents(torrentHash)
        if (not addTorrentToKeep(dataPath, torrentContent)):
            eprint(f"Торрент {torrent['name']} ({dataPath}) не хранится ни в одной из указаных дирректорий! "
                   f"Добавьте нужный путь в torrentsRoots")
        # print(dataPath)
        # print (json.dumps(torrentContent, sort_keys=True, indent=4, separators=(',', ': ')))
        # existingFiles = glob.glob('/home/huku/zitadelle-mirror/' + dataPath, recursive=True)
        # print(existingFiles)
        processedCount += 1
        if processedCount % 1000 == 0:
            printProcessedCount(processedCount, totalCount)
    if processedCount % 1000 != 0:
        printProcessedCount(processedCount, totalCount)
        print("Поиск осиротевших файлов..")
    for torrentRoot in torrentsRoots:
        checkFilesRecursive(torrentRoot)
    if simulate:
        print("Скрипт отработал корректно")
