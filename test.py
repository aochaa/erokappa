import re
 
get_msg = 'お化け退治をするなら http://hogehogepiyoyo.co.jp/ をみるといいよ'
 
print(get_msg)

get_msg = re.sub(r'(https?|ftp)(:\/\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+)', 'URL', get_msg)

print(get_msg)