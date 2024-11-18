import requests
import os

def download_file_requests(url, save_path):
    """
    使用 requests 下载文件，带进度条
    :param url: 下载链接
    :param save_path: 保存路径
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # 检查请求是否成功
        # 获取文件大小
        file_size = int(response.headers.get('content-length', 0))
        
        # 写入文件
        with open(save_path, 'wb') as file:
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
        print(f"文件已下载到: {save_path}")
        
    except Exception as e:
        print(f"下载失败: {str(e)}")

if __name__ == "__main__":
    ids = range(10259,10433)
    save_path = "D://data//"
    for id in ids:
        url = f"http://172.21.12.24:5001/api/polygon/tasks/{id}/result"
        download_file_requests(url, f"{save_path}{id}.csv")
