
import re

url_pattern = re.compile(r"""(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))""")

yt_pattern = re.compile(r"""^((?:https?:)?//)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(/(?:[\w\-]+\?v=|embed/|v/)?)([\w\-]+)(\S+)?$""")

rickroll_pattern = re.compile(
    r"""(?:(?:never[^\n\w]*(?:gonna[^\n\w]*)?)?(?:give[^\n\w]*you[^\n\w]*up|let[^\n\w]*you[^\n\w]*down))|rick[^\n\w]*roll"""
)

comment_pattern = re.compile(r"""(([nN]ever.*[gG]onna.*(give.*you.*up.*|let.*you.*down.*)|[rR]ick[^\n\w]?[rR]oll(e?d|ing|s|\'d)?)|wait*?\s*this\s*isn\'?t\s*[a-zA-Z\s]+|[rR]ick\s*[aA]stley\s*|([bB]ut)?\s*([tT]he)?[lL]ink\s*[sS](a|e)(id|yd|d)\s*[a-zA-Z\s]+)""")


