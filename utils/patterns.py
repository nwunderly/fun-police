
import re

url_pattern = re.compile(r"""(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))""")

yt_pattern = re.compile(r"""^((?:https?:)?//)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(/(?:[\w\-]+\?v=|embed/|v/)?)([\w\-]+)(\S+)?$""")

rick_roll_pattern = re.compile(
    r"""(?:(?:never[^\n\w]*(?:gonna[^\n\w]*)?)?(?:give[^\n\w]*you[^\n\w]*up|let[^\n\w]*you[^\n\w]*down))|rick[^\n\w]*roll"""
)
