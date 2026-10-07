#!/bin/bash
cd /home/zhaotianbing/world-corner-blog/public
exec python3 -m http.server 8900 --bind 0.0.0.0
