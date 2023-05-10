@Library('jenkins-shared-library') _

pipeline {
	agent any

	options {
		ansiColor('xterm')
		disableConcurrentBuilds()
	}

	environment {
		PYPI_TOKEN = credentials('pypi_token')
	}

	stages {
		stage('Checkout'){
			steps {
				checkout scm
			}
		}
		stage('Prep buildx') {
				steps {
						script {
								env.BUILDX_BUILDER = getBuildxBuilder();
						}
				}
		}
		stage('Dockerhub login') {
			steps {
				withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKERHUB_CREDENTIALS_USR', passwordVariable: 'DOCKERHUB_CREDENTIALS_PSW')]) {
					sh 'docker login -u $DOCKERHUB_CREDENTIALS_USR -p "$DOCKERHUB_CREDENTIALS_PSW"'
				}
			}
		}
		stage('Get Jenkins home source volume') {
			steps {
				script {
					env.JENKINS_HOME_VOL_SRC = getJenkinsDockerHomeVolumeSource();
				}
			}
		}
		stage('Build Docker Image') {
			steps {
				sh """
					docker buildx build --builder \$BUILDX_BUILDER --platform linux/amd64,linux/arm64 -t nbr23/watchmap:latest ${GIT_BRANCH == "master" ? "--push":""} .
					"""
			}
		}
		stage('Build python release') {
			steps {
				sh '''
				# If we are within docker, we need to hack around to get the volume mount path on the host system for our docker runs down below
				if docker inspect `hostname` 2>/dev/null; then
					REAL_PWD=$(echo $PWD | sed "s|$AGENT_WORKDIR|$JENKINS_HOME_VOL_SRC|")
				else
					REAL_PWD=$PWD
				fi
				docker run --rm -v $REAL_PWD:/app -w /app python:3-slim-buster bash -c "pip install poetry && poetry build"
				'''
			}
		}
		stage('Publish pypi package') {
			when { expression { sh([returnStdout: true, script: "git tag -l --contains $GIT_COMMIT | grep '^v' || true"]) } }
			steps {
				sh '''
				# If we are within docker, we need to hack around to get the volume mount path on the host system for our docker runs down below
				if docker inspect `hostname` 2>/dev/null; then
					REAL_PWD=$(echo $PWD | sed "s|$AGENT_WORKDIR|$JENKINS_HOME_VOL_SRC|")
				else
					REAL_PWD=$PWD
				fi
				docker run --rm -v $REAL_PWD:/app -w /app python:3-slim-buster bash -c "pip install poetry && poetry publish -n -u __token__ -p $PYPI_TOKEN"
				'''
			}
		}
		stage('Sync github repo') {
				when { branch 'master' }
				steps {
						syncRemoteBranch('git@github.com:nbr23/watchmap.git', 'master')
				}
		}
	}

	post {
		always {
			sh 'docker buildx stop $BUILDX_BUILDER || true'
			sh 'docker buildx rm $BUILDX_BUILDER'
			sh "sudo rm -rf ./dist"
		}
	}
}