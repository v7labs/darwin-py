HTTP_STATUS_OK=200
ERROR_UPDATE_REQUEST_FAILED=1

VERSION=`cat darwin/__init__.py | grep __version__ | cut -d'"' -f 2`
echo "Parsed version: $VERSION"

HTTP_STATUS=`curl -s -o /dev/null -w "%{http_code}" https://darwin.v7labs.com/api/healthcheck`
echo "HTTP status code received: $HTTP_STATUS"

if [ $HTTP_STATUS != $HTTP_STATUS_OK ]
then
	echo "Update request to backend server failed. Exiting."
	exit $ERROR_UPDATE_REQUEST_FAILED
fi

echo "Update request completed successfully."
