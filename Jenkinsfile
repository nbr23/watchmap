pipeline {
    agent any
    stages {
        stage('Checkout'){
            steps {
                checkout scm
            }
        }
        stage('Dockerhub login') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKERHUB_CREDENTIALS_USR', passwordVariable: 'DOCKERHUB_CREDENTIALS_PSW')]) {
                    sh 'docker login -u $DOCKERHUB_CREDENTIALS_USR -p "$DOCKERHUB_CREDENTIALS_PSW"'
                }
            }
        }
        stage('Build Docker Image') {
            steps {
                sh '''
                    BUILDER=`docker buildx create --use`
                    docker buildx build --platform linux/amd64,linux/arm64 -t nbr23/watchmap:latest --push .
                    docker buildx rm $BUILDER
                    '''
            }
        }
    }

    post {
        always {
            sh 'docker logout'
        }
    }
}