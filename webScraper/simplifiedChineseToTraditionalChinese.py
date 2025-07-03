from opencc import OpenCC

cc = OpenCC('s2t')  # s2t: Simplified to Traditional
def simplifiedChineseToTraditionalChinese(text_simplified):
    return cc.convert(text_simplified)
