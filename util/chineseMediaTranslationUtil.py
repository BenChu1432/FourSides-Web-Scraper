def map_chinese_media_to_enum(chinese_name: str) -> str:
    if chinese_name not in CHINESE_TO_ENGLISH_MEDIA:
        raise ValueError(f"❌ No mapping for media: {chinese_name}")
    return CHINESE_TO_ENGLISH_MEDIA[chinese_name]

CHINESE_TO_ENGLISH_MEDIA = {
    "華視": "CTS",
    "台灣時報": "TaiwanTimes",
    "台視": "TTV",
    "中視新聞": "CTINews",
    "自由時報": "LibertyTimesNet",
    "聯合新聞網": "UnitedDailyNews",
    "中國時報": "ChinaTimes",
    "中央社": "CNA",
    "公視": "PTSNews",
    "工商時報": "CTEE",
    "民眾日報": "MyPeopleVol",
    "中華日報": "ChinaDailyNews",
    "三立新聞網": "SETN",
    "蘋果新聞網": "NextAppleNews",
    "遠見":"GVM",
    "芋傳媒":"TaroNews",
    "鏡週刊": "MirrorMedia",
    "鏡報": "MirrorMedia",
    "NOWnews": "NowNews",
    "風傳媒": "StormMedia",
    "TVBS": "TVBS",
    "東森新聞": "EBCNews",
    "ETtoday": "ETtoday",
    "新頭殼": "NewTalk",
    "民視": "FTV",
    # Optional: Add HK/China-based ones if ever needed
    "人民日報": "PeopleDaily",
    "新華社": "XinhuaNewsAgency",
    "環球時報": "GlobalTimes",
    "中央電視台": "CCTV",
}
