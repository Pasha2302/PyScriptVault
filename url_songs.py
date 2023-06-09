import aiohttp
import os
import reading_writing_files as rwf
import asyncio
import headers_cookies as hc
# from pathlib import Path
from bs4 import BeautifulSoup as BS
from random import randint

import working_with_the_database as working_db


def split_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def get_url_songs(session: aiohttp.client.ClientSession, performer_data):
    count_err = 0
    performer_data['data_songs'] = []

    while True:
        try:
            response = await session.get(url=performer_data['url'], cookies=hc.cookies, headers=hc.headers)
            response_text = await response.text()

            soup = BS(response_text, 'lxml', multi_valued_attributes=None)
            check_tag = soup.find("body").text

            if 'Too Many Requests..' in check_tag:
                rwf.save_txt_data(data_txt=response_text, path_file='Erorr_Html_2.html')
                await asyncio.sleep(randint(2, 6))
                continue

            block_songs = soup.find("table", attrs={"id": "tablesort"})
            try:
                tags_url_song = block_songs.find_all("a", attrs={"class": "g-link"})
            except Exception as  err_html:
                print('\n', err_html)
                rwf.save_txt_data(data_txt=response_text, path_file='No_block_songs.html')
                break

            if tags_url_song:
                performer_data['data_songs'] = [
                    {"title": link_song.text.strip(), "url_song": link_song.get('href')} for link_song in tags_url_song
                ]
            break

        except Exception as err1:
            print(f'\n[39] err1 <{count_err}>', err1)
            if count_err > 4:
                print('>', end='')
                raise TypeError({'[41] ERROR': err1})
            count_err += 1
            await asyncio.sleep(6)
            continue

    print('>', end='')
    return performer_data


async def create_a_task_request(request_data, sess):
    data_list = []
    tasks_list = []
    exception_check = []

    for data in request_data:
        tasks_list.append(get_url_songs(sess, performer_data=data))

    res = await asyncio.gather(*tasks_list, return_exceptions=True)

    for data_validation in res:
        if not isinstance(data_validation, dict):
            exception_check.append(data_validation)
        else:
            data_list.append(data_validation)
    return data_list, exception_check


async def start_get_url_songs(session):
    if os.path.isfile('stop_index_url_songs.txt'):
        check_index_songs = int(rwf.download_txt_data('stop_index_url_songs.txt'))
    else:
        check_index_songs = 0
    exception_check = []
    tasks_list = []
    count_slice = 50

    performers_data_list = rwf.download_json_data(path_file='Performers_Data.json')
    request_data_slice = performers_data_list[check_index_songs:]
    count_total_data = len(performers_data_list)

    print("\n\n<<================= Идут запросы на получение ссылок на аккорды песен... =================>>")
    for data in split_list(request_data_slice, count_slice):
        res, exception_check = await create_a_task_request(request_data=data, sess=session)

        if exception_check:
            print('\nОшибки:')
            print(exception_check)
            return 0
        else:
            print('\nДанные получены')
            working_db.create_table_songs_and_add_data(data_list=res)
            # for json_data in res:
            #     rwf.save_json_complementing(json_data=json_data, path_file='Data_Songs.json', ind=True)

            check_index_songs += len(data)
            rwf.save_txt_data(data_txt=check_index_songs, path_file='stop_index_url_songs.txt')
            print(f"Запросов Выполнено: {check_index_songs} из {count_total_data}")
            print('==' * 40)

            # if check_index_songs % 200 == 0:
            #     break
