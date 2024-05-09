import requests
import os
import shutil
import zipfile
import argparse
import re
from bs4 import BeautifulSoup

def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 找到所有 id 为 accordion 的 div 元素
    accordion_divs = soup.find_all('div', {'id': 'accordion'})
    
    result = []
    
    # 遍历每个 accordion_div
    for accordion_div in accordion_divs:
        # 找到当前 accordion_div 下的所有子 div 元素
        child_divs = accordion_div.findChildren('div', recursive=False)
        
        # 遍历每个子 div
        for child_div in child_divs:
            # 找到含有 data-link 标签的第一个 div 元素
            first_div_with_data_link = child_div.find(attrs={'data-link': True})
            
            # 如果找到了符合条件的 div，则将其内容添加到结果数组中
            if first_div_with_data_link:
                result.append(first_div_with_data_link['data-link'])
    
    return result

def download_and_extract(url, output_dir, cache='./cache'):
    # 发送请求
    response = requests.get(url)
    if response.status_code == 200: 
        
        items = parse_html(response.text)
        data_links = [item for item in items if re.match(r'^Atmel\.SAM', item)] 
         
        os.makedirs(cache,exist_ok=True)
        os.makedirs(output_dir,exist_ok=True)
        # 下载并解压文件
        for link in data_links:
            # 构建下载路径
            download_url = os.path.join(url, link)
            
            # 下载文件到临时目录
            atpack_filename = os.path.basename(download_url)
            atpack_path = os.path.join(cache, atpack_filename)
            # 如果文件不存在则下载
            if not os.path.exists(atpack_path):
                with open(atpack_path, 'wb') as f:
                    f.write(requests.get(download_url).content)
            
            matched = re.search(r'^Atmel\.(.*?)\.', atpack_filename)
            series = matched.group(1);
            # 解压到指定目录的同名文件夹下
            with zipfile.ZipFile(atpack_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(output_dir, series))
 
def generate_header(input_dir,output_dir):
    print(input_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download and extract files from a webpage.')
    parser.add_argument('--url', help='URL of the webpage to scrape', default='http://packs.download.atmel.com/')
    parser.add_argument('--output-dir', help='Output directory for extracted files', default='./Atmel')
    parser.add_argument('--cache', help='Web download cache', default='./cache')
    args = parser.parse_args()
    
    # 检查输出目录是否存在，如果不存在则创建
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    temp_dir = "./temp"
    download_and_extract(args.url, temp_dir)
    generate_header(temp_dir, args.output_dir)
    shutil.rmtree(temp_dir)
