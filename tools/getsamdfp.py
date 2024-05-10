import requests
import os
import shutil
import zipfile
import argparse
import re
from bs4 import BeautifulSoup

def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # �ҵ����� id Ϊ accordion �� div Ԫ��
    accordion_divs = soup.find_all('div', {'id': 'accordion'})
    
    result = []
    
    # ����ÿ�� accordion_div
    for accordion_div in accordion_divs:
        # �ҵ���ǰ accordion_div �µ������� div Ԫ��
        child_divs = accordion_div.findChildren('div', recursive=False)
        
        # ����ÿ���� div
        for child_div in child_divs:
            # �ҵ����� data-link ��ǩ�ĵ�һ�� div Ԫ��
            first_div_with_data_link = child_div.find(attrs={'data-link': True})
            
            # ����ҵ��˷��������� div������������ӵ����������
            if first_div_with_data_link:
                result.append(first_div_with_data_link['data-link'])
    
    return result

def clean_folders(base_folder):
    # ����base_folder�µ�ÿ�����ļ���
    for root, dirs, files in os.walk(base_folder):
        # ��鵱ǰ�ļ������Ƿ���'include'�ļ���
        if 'include' in dirs: 
            # ������ǰ�ļ����µ��������ļ���
            for dir in dirs:
                if dir not in ['gcc', 'include']:
                    # �����������ļ���·��
                    full_dir_path = os.path.join(root, dir)
                    # ɾ������'gcc'��'include'���ļ���
                    shutil.rmtree(full_dir_path)
                    print(f"deleted folder: {full_dir_path}")
                    
def download_and_extract(url, output_dir, cache='./cache'):
    # ��������
    response = requests.get(url)
    if response.status_code == 200: 
        
        items = parse_html(response.text)
        data_links = [item for item in items if re.match(r'^Atmel\.SAM', item)] 
         
        os.makedirs(cache,exist_ok=True)
        os.makedirs(output_dir,exist_ok=True)
        # ���ز���ѹ�ļ�
        for link in data_links:
            # ��������·��
            download_url = os.path.join(url, link)
            
            # �����ļ�����ʱĿ¼
            atpack_filename = os.path.basename(download_url)
            atpack_path = os.path.join(cache, atpack_filename)
            # ����ļ�������������
            if not os.path.exists(atpack_path):
                with open(atpack_path, 'wb') as f:
                    f.write(requests.get(download_url).content)
                    
            
            series = re.search(r'^Atmel\.(.*?)\.', atpack_filename).group(1)
            version = re.search(r"DFP\.(\d+\.\d+\.\d+)(?:\.atpack)?", atpack_filename).group(1)
            # ��ѹ��ָ��Ŀ¼��ͬ���ļ�����
            with zipfile.ZipFile(atpack_path, 'r') as zip_ref:
                series_dir = os.path.join(output_dir, series, version)
                os.makedirs(series_dir,exist_ok=True)
                zip_ref.extractall(series_dir)
                print(f"create folder: {series_dir}")
 
def generate_header(input_dir,output_dir):
    #clean_folders(input_dir)
    print(input_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download and extract files from a webpage.')
    parser.add_argument('--url', help='URL of the webpage to scrape', default='http://packs.download.atmel.com/')
    parser.add_argument('--output-dir', help='Output directory for extracted files', default='./Atmel')
    parser.add_argument('--cache', help='Web download cache', default='./cache')
    args = parser.parse_args()
    
    # ������Ŀ¼�Ƿ���ڣ�����������򴴽�
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    temp_dir = "./temp"
    download_and_extract(args.url, temp_dir)
    generate_header(temp_dir, args.output_dir)
    #shutil.rmtree(temp_dir)
