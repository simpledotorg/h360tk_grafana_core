. getenv.sh


###
# Tags versions
#
# Five tags per component, from the list in getenv.sh. Adding an image is a
# one-word change there - this file does not need touching.
###
for component in ${COMPONENTS}; do
    for tag in \
        "latest" \
        "${BRANCH_NAME}" \
        "${BRANCH_NAME}.${BUILD_NUMBER}" \
        "${BRANCH_NAME}.${COMMIT_HASH}" \
        "${COMMIT_HASH}"
    do
        echo "tagging heart360tk-${component} as ${DOCKER_REPO}/heart360tk-${component}:${tag}"
        docker tag "heart360tk-${component}" "${DOCKER_REPO}/heart360tk-${component}:${tag}"
    done
done
