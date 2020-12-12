git pull

docker build . --tag funpolice:latest

docker run -d \
 --name funpolice \
 --network prod \
 -v $PWD/logs:/funpolice/logs \
 --restart unless-stopped \
 funpolice
