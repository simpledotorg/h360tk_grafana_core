. getenv.sh


###
# Pushes Versions
#
# Mirrors dockertag.sh: same component list from getenv.sh, same five tags.
###
for component in ${COMPONENTS}; do
    for tag in \
        "latest" \
        "${BRANCH_NAME}" \
        "${BRANCH_NAME}.${BUILD_NUMBER}" \
        "${BRANCH_NAME}.${COMMIT_HASH}" \
        "${COMMIT_HASH}"
    do
        echo "pushing ${DOCKER_REPO}/heart360tk-${component}:${tag}"
        docker push "${DOCKER_REPO}/heart360tk-${component}:${tag}"
    done
done
