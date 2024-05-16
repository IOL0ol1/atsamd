import argparse
from glob import iglob
import json
import requests
import os
import shutil
import zipfile
import re
import xml.etree.ElementTree as ET
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

def clean_folders(base_folder):
    # 遍历base_folder下的每个子文件夹
    for root, dirs, files in os.walk(base_folder):
        for filename in files:
            # Check if the file name is 'package.content' or has extension '.pdsc'
            if filename == 'package.content' or filename.endswith('.pdsc'):
                file_path = os.path.join(root, filename)
                # Delete the file
                os.remove(file_path)
        # 检查当前文件夹中是否有'include'文件夹
        if 'include' in dirs: 
            # 遍历当前文件夹下的所有子文件夹
            for dir in dirs:
                if dir not in ['gcc', 'include']:
                    # 构造完整的文件夹路径
                    full_dir_path = os.path.join(root, dir)
                    # 删除不是'gcc'或'include'的文件夹
                    shutil.rmtree(full_dir_path)
                    print(f"deleted folder: {full_dir_path}")
                    
def download_and_extract(url, atmel_dir, cmsis_dir, cache_dir):
    # 发送请求
    response = requests.get(url)
    if response.status_code == 200: 
        
        items = parse_html(response.text)
        atpack_links = [item for item in items if re.match(r'(^Atmel\.SAM)|(^ARM\.CMSIS)', item)] 
         
        os.makedirs(atmel_dir,exist_ok=True)
        os.makedirs(cmsis_dir,exist_ok=True)
        os.makedirs(cache_dir,exist_ok=True)
        # 下载并解压文件
        for link in atpack_links:
            # 构建下载路径
            download_url = os.path.join(url, link)
            
            # 下载文件到临时目录
            atpack_name = os.path.basename(download_url)
            atpack_path = os.path.join(cache_dir, atpack_name)
            # 如果文件不存在则下载
            if not os.path.exists(atpack_path):
                with open(atpack_path, 'wb') as f:
                    print(f"download file: {download_url}")
                    f.write(requests.get(download_url).content)
                    
            groups = re.search(r'[^.]+\.(.*?)\.(.+)\.atpack', atpack_name)
            series = groups.group(1)
            version = groups.group(2)
            # 解压到指定目录的同名文件夹下
            with zipfile.ZipFile(atpack_path, 'r') as zip_ref:
                series_dir = os.path.join(atmel_dir, series, version)
                if(series == "CMSIS"):
                    series_dir = os.path.join(cmsis_dir, version)
                os.makedirs(series_dir,exist_ok=True)
                zip_ref.extractall(series_dir)
                print(f"create folder: {series_dir}")
 
def get_devices(pdsc_file):
    devices = []
    # 查找devices节点下的family节点
    family_nodes = ET.parse(pdsc_file).getroot().findall('.//devices/family')
    # 输出family节点以及其下的device节点
    for family_node in family_nodes: 
        # 获取family节点下的device节点
        device_nodes = family_node.findall('device')
        for device_node in device_nodes:
            device = {}
            root = os.path.dirname(pdsc_file)
            device['root'] = root
            device['series'] = family_node.get('Dfamily')
            device['device'] = device_node.get('Dname')
            device['core'] = device_node.find('processor').get('Dcore') 
            device['endian'] = device_node.find('processor').get('Dendian') 
            device['mpu'] = device_node.find('processor').get('Dmpu') 
            device['fpu'] = device_node.find('processor').get('Dfpu') 
            device['header'] = device_node.find('compile').get('header') 
            device['define'] = device_node.find('compile').get('define')
            
            for memory_node in device_node.findall("./memory[@default]"):
                if 'startup' in memory_node.attrib:
                    flash_memory = memory_node
                    device['romstart'] = flash_memory.get('start')
                    device['romsize'] = flash_memory.get('size')
                else:
                    ram_memory = memory_node
                    device['ramstart'] = ram_memory.get('start')
                    device['ramsize'] = ram_memory.get('size')
            atdf = device_node.find('.//at:atdf',{'at': 'http://www.atmel.com/schemas/pack-device-atmel-extension'}).get('name')
            atdf_file = os.path.join(root,atdf)
            atdf_root = ET.parse(atdf_file).getroot();
            device['family'] = atdf_root.find('.//devices/device').get('family')
            device['defines'] = {}
            for parame_node in atdf_root.find('.//devices/device/parameters').findall('param'):
                device['defines'][parame_node.get('name')] = parame_node.get('value') + 'U'
            devices.append(device)
    return devices
 
def get_all_devices(folder):
    devices = []
    for file in  [file for file in iglob(os.path.join(folder, '**/*.pdsc'), recursive=True)]:
        devices.extend(get_devices(file))
    return devices
    


if __name__ == "__main__":
    cd = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(cd)
    parser = argparse.ArgumentParser(description='Download and extract files from a webpage.')
    parser.add_argument('--url', help='URL of the webpage to scrape', default='http://packs.download.atmel.com/')
    parser.add_argument('--output_atmel', help='Output directory for extracted atmel files', default= os.path.join(root, 'system', 'Atmel'))
    parser.add_argument('--output_cmsis', help='Output directory for extracted cmsis files', default= os.path.join(root, 'system', 'CMSIS'))
    parser.add_argument('--cache', help='Web download cache', default='cache')
    args = parser.parse_args()
     
    download_and_extract(args.url, args.output_atmel , args.output_cmsis, "cache") 
    devices = get_all_devices(args.output_atmel)
    clean_folders(args.output_atmel)
    with open("data.json", "w") as file:
        file.write(json.dumps(devices,indent=4))
    #shutil.rmtree(temp_dir)
