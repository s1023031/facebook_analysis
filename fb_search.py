import json
import datetime
import csv
import time

import pymongo
from pymongo import MongoClient

client = MongoClient("140.120.13.242",27017)
print(client)

# db= client["fb_analysis_v2"]
# col=db["fp_content"]

# file_id = ["2017CSIEBACCARAT"]
# file_name=["資百樂"]
# col_names=["co2017CSIEBACCARAT"]
# col_dict=dict() # collection名稱
# dic=dict() # 粉專名稱
# for i in range(len(file_id)):
#     dic[file_id[i]]=file_name[i]
#     col_dict[file_id[i]]=col_names[i]

db= client["fb_analysis_v2"]
col=db["person_info"]

while(1):
	name=input("輸入名字: ")
	if name=='exit': # 離開程式
		break

	cursor=col.find({"name":name})
	
	if cursor.count()<=0:
		print("this user cannot be found\n")
		continue

	dic=dict() # 所有的相同的name會存在這裡
	for arr in cursor:
		print(arr["id"],"/",arr["name"])
		dic[arr["id"]]=arr["name"]

	while(1):
		user_id=input("請輸入id: ")
		if user_id=='exit':
			break
		cursor=col.find({"id":user_id}).limit(1)
		if cursor.count()<=0:
			print("沒有這個id\n")
			continue
		for arr in cursor:
			comment_list=arr['comment_list']
			for cmd in comment_list:
				print(cmd)
		while(1):
			search_mode=input("要看哪個粉專呢?(all 可以看全部)")
			if search_mode=='exit':
				break
			elif search_mode=='all':
				for fanPage in comment_list:
					com_col=db[fanPage] # 切換資料表
					cursor=com_col.find({"id":user_id})
					if cursor.count() >0:
						for content in cursor:
							print(content,'\n')
			else:
				if search_mode not in comment_list:
					print("是不是打錯字了?\n")
					continue
				com_col=db[search_mode] # 切換資料表
				cursor=com_col.find({"id":user_id})
				if cursor.count() >0:
					for content in cursor:
						print(content,'\n')
			# print(arr['comment_list'])
			# dic[arr["id"]]=arr["name"]


 

