from news import News, MingPaoNews, OrientalDailyNews,WenWeiPo,TaKungPao,HK01,InMediaHK,InitiumMedia,TheWitness,RTHK,HKET,HKEJ,TheStandard,HKFreePress,OrangeNews,HKGovernmentNews,ICable,HKCD,TheEpochTimes,HKCourtNews,NowTV,ChineseBBC,VOC,DeutscheWelle,ChineseNewYorkTimes,PeopleDaily,XinhuaNewsAgency,GlobalTimes, CCTV,ChinaTimes,LibertyTimesNet,CNA,TaiwanEconomicTimes,CTEE,TaiwanTimes,ChinaDailyNews,NextAppleNews,MirrorMedia, NowNews, TVBS,EBCNews, NewTalk,FTV

url = "https://www.ftvnews.com.tw/news/detail/2025701W0826"
article =FTV(url)

print("Title:", article.title)
print("Content:", article.content)  # show first 300 chars


