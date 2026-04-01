from urllib import response

from   my_llm import llm

respon = llm.invoke("用三句话，介绍机器学习")

print(respon)
print(type(respon))
