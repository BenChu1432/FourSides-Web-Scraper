from opencc import OpenCC

# Create a converter: Simplified to Traditional
cc = OpenCC('s2tw')  # Other options: t2s, s2tw, s2hk, s2twp


def translateIntoTraditionalChinese(text:str):
    return cc.convert(text)