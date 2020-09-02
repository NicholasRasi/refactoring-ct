pipeline {
  options { disableConcurrentBuilds() }
  agent { label 'docker-slave' }
  stages {
    stage ('Pull repo code from github') {
      steps {
        checkout scm
      }
    }
    stage('test ct-refactoring') {
        steps {
            sh "pip3 install -r requirements.txt"
            sh "pip3 install -e ."
            sh "python3 -m pytest --pyargs -s ${WORKSPACE}/tests" --junitxml="results.xml" --cov=components --cov=models --cov-report xml tests/
            junit 'results.xml'
        }
    }
    stage('SonarQube analysis'){
        environment {
          scannerHome = tool 'SonarQubeScanner'
        }
        steps {
            withSonarQubeEnv('SonarCloud') {
                      sh "${scannerHome}/bin/sonar-scanner"
            }
        }
    }
  }
  post {
    failure {
        slackSend (color: '#FF0000', message: "FAILED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
    }
    fixed {
        slackSend (color: '#6d3be3', message: "FIXED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})") 
    }
  }
}