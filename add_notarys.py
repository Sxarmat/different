import re
import requests
from bs4 import BeautifulSoup
from fast_bitrix24 import Bitrix

BX24 = Bitrix('Webhook')
URL = 'https://data.notariat.ru/api/directory/html/notary-list/?is_active=True&chamber__region_id=56'
RESPONSE_ID = 158

def add_notarys(url):
    notary_links = get_notarys_links(url)
    notarys_data = list(map(get_notary_data, notary_links))
    params = get_params_bx24(notarys_data)
    return BX24.call('crm.company.add', params)


def get_notarys_links(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'lxml')
    notarys = soup.find_all('a', class_='notary-list-item__link js-notary-card')
    links = map(lambda notary: notary['href'], notarys)
    return links


def get_notary_data(link):
    html = requests.get(link).text
    soup = BeautifulSoup(html, 'lxml')
    notary_info = soup.find_all('div', class_='info')
    contacts = notary_info[0].find_all('div', class_='info__block', limit=2)
    correct_phone_comment = corrector_phone_comment(notary_phone=contacts[1].p.text, notary_comment=notary_info[1].text)
    notary_data = {
        'full_name': soup.find('h3', class_='notary__name').text.strip(),
        'address': contacts[0].p.text,
        'phone': correct_phone_comment[0],
        'comment': correct_phone_comment[1]
    }
    return notary_data


def corrector_phone_comment(**kwargs):
    phone = kwargs['notary_phone']
    comment = kwargs['notary_comment']
    pattern_phone = r'\(|\)|-|\s'
    phone = re.sub(pattern_phone, '', phone)
    if len(phone) == 10:
        phone = '+7' + phone
    elif len(phone) == 11:
        if phone[0] == '8':
            phone = '+7' + phone[1:]
        elif phone[0] == '7':
            phone = '+' + phone
    comment_pattern = r'\s{2,}'
    comment = re.sub(comment_pattern, '\n', comment).strip()
    comment = '<br>'.join(comment.split('\n'))
    return phone, comment


def get_params_bx24(data_list):
    params = [
        {
            'fields':
                {
                    'TITLE': '{} (нотариус)'.format(data['full_name']),
                    'COMPANY_TYPE': '1',
                    'ADDRESS': data['address'],
                    'COMMENTS': data['comment'],
                    'ASSIGNED_BY_ID': RESPONSE_ID,
                    'INDUSTRY': '1',
                    'PHONE': [{'VALUE': data['phone'], 'VALUE_TYPE': 'WORK'}],
                    'OPENED': 'Y'
                }
        }
        for data in data_list
    ]
    return params


if __name__ == '__main__':
    add_notarys(URL)
