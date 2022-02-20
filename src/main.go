package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"time"
)

const (
	cookieName            = "nibble_auth_token"
	cookieMaxAge          = 3600 * 24
	defaultPort           = "10001"
	tokenParamName        = "token"
	redirectParamName     = "redirect_to"
	defaultRedirectUrl    = "/"
	defaultAuthEndpoint   = "/auth"
	configLocationEnvVar  = "NIBBLE_CONFIG_LOCATION"
	defaultConfigLocation = "/etc/nibble/config.json"
)

type NibbleConfig struct {
	Token      string `json:"token"`
	WorkingDir string `json:"working_dir"`
}

type AuthMethod int

const (
	None AuthMethod = iota
	Cookie
	QueryParam
)

func main() {
	port := flag.String("p", defaultPort, "port to listen on")
	endpoint := flag.String("e", defaultAuthEndpoint, "URL path to where service is accesible")
	flag.Parse()

	http.HandleFunc(*endpoint, authHandler)

	log.Printf("Launching auth service at '%s' on port %s...", *endpoint, *port)
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%s", *port), nil))
}

func authHandler(w http.ResponseWriter, r *http.Request) {
	// Reading the config at each requests ensure that we don't need
	// to restart the service if config is updated at runtime.
	configFilePath := getConfigFilePath()
	log.Printf("Parsing config from '%s'...", configFilePath)
	config := parseConfigFile(configFilePath)

	token, authMethod := getAuthToken(r)
	isAuthenticated := authenticate(config, token)
	if !isAuthenticated {
		log.Println("Authentication failed")
		w.WriteHeader(http.StatusForbidden)
		return
	}

	log.Println("Authentication succeeded")
	if authMethod != Cookie {
		// Set cookie only if it was not used as authentication method, to avoid
		// reseting original expiration time.
		cookie := buildAuthCookie(r.Host, config)
		log.Println("Setting authentication cookie...")
		http.SetCookie(w, &cookie)
	}

	redirectionUrl := getRedirectionUrl(r)
	log.Println("Redirecting...")
	http.Redirect(w, r, redirectionUrl, 302)
}

func getConfigFilePath() string {
	configLocation, ok := os.LookupEnv(configLocationEnvVar)
	if ok {
		return configLocation
	}
	return defaultConfigLocation
}

func parseConfigFile(configFilePath string) NibbleConfig {
	config := NibbleConfig{}
	configData, err := os.ReadFile(configFilePath)
	if err != nil {
		log.Printf("Error while reading config file: '%s'", err)
	} else {
		err := json.Unmarshal([]byte(configData), &config)
		if err != nil {
			log.Printf("Error parsing config JSON data: '%s'", err)
		}
	}
	return config
}

func authenticate(config NibbleConfig, token string) bool {
	time.Sleep(100 * time.Millisecond)
	return config.Token == token
}

func getAuthToken(r *http.Request) (string, AuthMethod) {
	cookieToken, err := getTokenFromCookie(r)
	if err != nil {
		queryParamToken, err := getTokenFromUrlQueryParam(r)
		if err != nil {
			log.Println("User token not found")
			return "", None
		}
		return queryParamToken, QueryParam
	}
	return cookieToken, Cookie
}

func getTokenFromUrlQueryParam(r *http.Request) (string, error) {
	urlToken, ok := r.URL.Query()[tokenParamName]
	if !ok || len(urlToken[0]) < 1 {
		return "", fmt.Errorf("Token not found in URL query params.")
	}
	log.Println("User token found in query params")
	return urlToken[0], nil
}

func getTokenFromCookie(r *http.Request) (string, error) {
	cookieToken, err := r.Cookie(cookieName)
	if err != nil {
		return "", err
	}
	log.Println("User token found in auth cookie")
	return cookieToken.Value, nil
}

func getRedirectionUrl(r *http.Request) string {
	redirectUrl, ok := r.URL.Query()[redirectParamName]
	if !ok || len(redirectUrl[0]) < 1 {
		log.Println("Redirection URL not found in query params.")
		return defaultRedirectUrl
	}
	return redirectUrl[0]
}

func buildAuthCookie(host string, config NibbleConfig) http.Cookie {
	domain, _, _ := net.SplitHostPort(host)

	return http.Cookie{
		Name:     cookieName,
		Value:    config.Token,
		MaxAge:   cookieMaxAge,
		Domain:   domain,
		Expires:  time.Now().Add(time.Second * time.Duration(cookieMaxAge)),
		HttpOnly: true,
		Secure:   true,
	}
}
