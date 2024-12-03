import pandas as pd

if __name__ == "__main__":
    df = pd.read_csv('c:/Users/TST/polygon_tasks.csv')
    #对第三列去重
    #df = df.drop_duplicates(subset=['polygon'])
    #查看重复数据
    # 查看第4列的重复值
    duplicates = df[df.duplicated(subset=[df.columns[4]], keep=False)].sort_values(by=df.columns[4])
    print("重复的行：")
    print(duplicates)
