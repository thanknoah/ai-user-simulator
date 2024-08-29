#include <iostream>
#include <fstream>
#include <iostream>
#include <asio.hpp>
#include <thread>
#include <regex>
#include <algorithm>
#include <string>
#include <cstring>
#include <future>
#include <regex>
#include <random>
#include <nlohmann/json.hpp>
#include <mysql_driver.h>
#include <mysql_connection.h>
#include <cppconn/statement.h>
#include <cppconn/resultset.h>
#include <sstream>
#include <iomanip>
#include <cctype>
#include <mutex>
#include <condition_variable>
#include <memory>

using asio::ip::tcp;
using json = nlohmann::json;

// Essential Global Variables
asio::io_context ioContext;
tcp::resolver resolver(ioContext);
tcp::resolver::results_type endPoints;
std::shared_ptr<tcp::socket> serverSocket;
std::mutex mtxPosts;
std::mutex mtxComments;
std::string cvPostResp;
std::string cvCommentsResp;
std::condition_variable cvPosts; 
std::condition_variable cvComments;

void activateAIServerListener() {
    try {
        // use shared_ptr to manage the lifetime of the AI server
        serverSocket = std::make_shared<tcp::socket>(ioContext);
        endPoints = resolver.resolve("127.0.0.1", "62131");
        auto socket = std::make_shared<tcp::socket>(ioContext);
        auto sizeBuffer = std::make_shared<std::array<char, sizeof(uint32_t)>>();

        // Connect and establish mutex
        std::lock_guard<std::mutex> lockPost(mtxPosts);
        std::lock_guard<std::mutex> lockPost2(mtxComments);
        asio::connect(*serverSocket, endPoints);

        // Async read the size of the response
        asio::async_read(*serverSocket, asio::buffer(*sizeBuffer),
            [sizeBuffer, socket](asio::error_code ec, std::size_t /*len*/) {
                if (!ec) {
                    // Assign size of the content to size 
                    uint32_t size;
                    std::memcpy(&size, sizeBuffer->data(), sizeof(uint32_t));
                    size = ntohl(size);
                    auto dataBuffer = std::make_shared<std::vector<char>>(size);

                    // Asynchronously read the data
                    asio::async_read(*serverSocket, asio::buffer(*dataBuffer),
                        [dataBuffer, socket](asio::error_code ec, std::size_t) {
                            if (!ec) {
                                std::string resp(dataBuffer->begin(), dataBuffer->end());
                                cvPostResp = resp;
                                cvPosts.notify_one();
                                //cvComments.notify_one();
                            }
                            else {
                                std::cout << "Error reading data: " << ec.message() << std::endl;
                            }
                        });
                }
                else {
                    std::cout << "Error reading size: " << ec.message() << std::endl;
                }
            });

        ioContext.run();
    }
    catch (std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
    }
}

std::string getAPIResponse(tcp::socket& socket) {
    asio::streambuf resp;
    asio::read_until(socket, resp, "\r\n\r\n");
    std::istream resp_stream(&resp); std::stringstream resp_body; std::string header;
    asio::error_code ec;

    while (std::getline(resp_stream, header) && header != "\r");

    if (resp.size() > 0) {
        resp_body << &resp;
    }
    while (asio::read(socket, resp, asio::transfer_at_least(1), ec)) {
        resp_body << &resp;
    }

    std::string resp_body_str = resp_body.str();
    return resp_body_str;
}

int returnAmountOfLines(std::string fileName) {
    std::ifstream inputFile(fileName);
    std::string line;
    int lineCount = 0;

    while (std::getline(inputFile, line)) {
        lineCount++;
    }
    inputFile.close();

    return lineCount;
}

std::string generateRequestHeader(std::string path) {
    std::string request = "GET " + path + " HTTP/1.1\r\n";
    request += "Host: thenoahdevs.com\r\n";
    request += "Accept: application/json\r\n";
    request += "Connection: close\r\n\r\n";

    return request;
}

int generateRandomIndex(int maxLen) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1, maxLen);
    return dis(gen);
}

void capitalizeString(std::string& str) {
    std::transform(str.begin(), str.end(), str.begin(),
        [](unsigned char c) { return std::toupper(c); });
}

void lowercaseString(std::string& str) {
    std::transform(str.begin(), str.end(), str.begin(),
        [](unsigned char c) { return std::tolower(c); });
}


std::string urlEncode(const std::string& value) {
    std::ostringstream encoded;
    encoded << std::hex << std::uppercase;
    for (char c : value) {
        if (std::isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_' || c == '.' || c == '~') {
            encoded << c;
        }
        else {
            encoded << '%' << std::setw(2) << std::setfill('0') << static_cast<int>(static_cast<unsigned char>(c));
        }
    }
    return encoded.str();
}

void registerRandomUsers(asio::io_context& ioContext, std::string& host, std::string& path) {
    try {
        tcp::resolver resolver(ioContext);
        tcp::resolver::results_type endPoints = resolver.resolve(host, "80");
        tcp::socket socket(ioContext);
        asio::connect(socket, endPoints);

        std::string request = generateRequestHeader(path);
        asio::write(socket, asio::buffer(request));
        std::string resp_body_str = getAPIResponse(socket);
        std::string resp_body_str_without_quotations = std::regex_replace(resp_body_str, std::regex("\""), "");
        std::size_t found = resp_body_str.find("Exists");

        if (found != std::string::npos) {
            std::cout << "Error: Username is repeat";
        }
        else {
            std::ofstream outfile("tokens.txt", std::ios::app);
            if (!outfile) { std::cerr << "Error opening file"; }
            outfile << resp_body_str_without_quotations << std::endl;
            outfile.close();
        }
    }
    catch (std::exception& e) {
        std::cerr << e.what();
    }

}

std::vector<std::string> generateRandomComment(json posts) {
    try {
        while (true) {
            sql::mysql::MySQL_Driver* driver;
            sql::Connection* con;

            driver = sql::mysql::get_mysql_driver_instance();
            con = driver->connect("[REDACTED]", "[REDACTED]", "[REDACTED]");
            con->setSchema("[REDACTED]");

            sql::Statement* stmt = con->createStatement();
            sql::ResultSet* res = stmt->executeQuery("SELECT id FROM posts ORDER BY id DESC LIMIT 10");

            while (res->next()) {
                std::cout << "The message is: " << res->getString("_message") << std::endl;
            }

            // Write to file
            asio::write(*serverSocket, asio::buffer("generate_title_desc"));
            std::vector listOfComments;

            // Wait for Response && Converting the resp str into json
            std::unique_lock<std::mutex> lockPost2(mtxComments);
            cvComments.wait(lockPost2, [] { return "Ready"; });
            lockPost2.unlock();

            // Turning it into Json
            json obj = json::parse(cvCommentsResp);
            std::vector<std::string> listOfComments;
        }
    }
    catch (std::exception& e) {
        std::cerr << e.what();
    }
}

std::vector<std::string> generateRandomPosts() {
    try {
        // Token File Length
        std::future<int> tokenLen = std::async(std::launch::async, returnAmountOfLines, "tokens.txt");
        int tokenCount = tokenLen.get();

        // Write to file && socket
        std::ifstream token("tokens.txt");
        std::string token_;
        asio::write(*serverSocket, asio::buffer("generate_title_desc"));

        // Wait for Response && Converting the resp str into json
        std::unique_lock<std::mutex> lockPost(mtxPosts);
        cvPosts.wait(lockPost, [] { return "Ready"; });
        lockPost.unlock();
        json obj = json::parse(cvPostResp);
        std::vector<std::string> listOflinks;

        // Looping through json
        for (auto it = obj.begin(); it != obj.end(); ++it) {
            std::string title = it.key();
            std::string desc = it.value();

            title.erase(std::remove(title.begin(), title.end(), '\n'), title.end());
            title.erase(std::remove(title.begin(), title.end(), '"'), title.end());
            desc.erase(std::remove(desc.begin(), desc.end(), '\n'), desc.end());
            desc.erase(std::remove(desc.begin(), desc.end(), '"'), desc.end());

            // Choosing random token
            for (int y = 0; y < generateRandomIndex(tokenCount-1); y++)
                std::getline(token, token_);
            
            std::cout << token_;
            std::string link = "[REDACTED]";
            listOflinks.push_back(link);
        }

        token.close();
        return listOflinks;
    }
    catch (std::exception& e) {
        std::cerr << e.what();
    }
}

std::string generateRandomUser() {
    try {
        std::future<int> namesLength = std::async(std::launch::async, returnAmountOfLines, "names.txt");
        std::future<int> adjectivesLength = std::async(std::launch::async, returnAmountOfLines, "adjectives.txt");
        std::future<int> pfpLength = std::async(std::launch::async, returnAmountOfLines, "pfp.txt");

        int namesCount = namesLength.get();
        int adjectivesCount = adjectivesLength.get();
        int pfpCount = pfpLength.get();

        std::ifstream names("names.txt");
        std::ifstream adjectives("adjectives.txt");
        std::ifstream pfp("pfp.txt");
        std::string adjectives_;
        std::string names_;
        std::string pfpLink;
        std::string numbers;

        for (int y = 0; y < generateRandomIndex(adjectivesCount - 1); y++)
            std::getline(adjectives, adjectives_);

        for (int y = 0; y < generateRandomIndex(namesCount - 1); y++)
            std::getline(names, names_);

        for (int y = 0; y < generateRandomIndex(pfpCount - 1); y++)
            std::getline(pfp, pfpLink);

        int grammarType = generateRandomIndex(5);
        int numLen = generateRandomIndex(5);
        int maxNum = 1;

        if (grammarType == 1 || grammarType == 2) { capitalizeString(adjectives_); capitalizeString(names_); }
        if (grammarType == 3 || grammarType == 4) { lowercaseString(adjectives_); lowercaseString(names_); }

        for (int x = 0; x < numLen; x++) {
            maxNum = maxNum * 10;
        }
        numbers = std::to_string(generateRandomIndex(maxNum));

        names.close();
        adjectives.close();
        pfp.close();

        return "[REDACTED]";
    }
    catch (std::error_code ec) {
        std::cerr << "Error: " << ec;
    }
    
}

void intializeUserGeneration() {
    asio::io_context ioContext;
    std::string pfpLink = "example";
    std::string host = "thenoahdevs.com";

    // Create 20 users every 20 seconds
    while (true) {
        for (int x = 0; x < 20; ++x) {
            std::string path = generateRandomUser();
            registerRandomUsers(ioContext, host, path);
            std::cout << "Sent link too " << path << "\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(3));
        }
        std::this_thread::sleep_for(std::chrono::seconds(10));
    }
}

void initializePostGeneration() {
    asio::io_context ioContext;
    std::cout << "Starting..";

    while (true) {
        std::vector<std::string> listOfLinks = generateRandomPosts();

        for (auto& it : listOfLinks) {
            tcp::resolver resolver(ioContext);
            tcp::resolver::results_type endPoints = resolver.resolve("thenoahdevs.com", "80");
            tcp::socket socket(ioContext);
            asio::connect(socket, endPoints);

            std::string request = generateRequestHeader(it);
            asio::write(socket, asio::buffer(request));
            std::cout << "Generated new post at https://thenoahdevs.com/" + it + "\n";
        }
        std::this_thread::sleep_for(std::chrono::seconds(15));
    }
}

void initializePfpImageGeneration() {
    for (int x = 0; x < 20; x++) {
        asio::io_context ioContext;
        tcp::resolver resolver(ioContext);
        tcp::resolver::results_type endPoints = resolver.resolve("127.0.0.1", "62001");
        tcp::socket socket(ioContext);

        asio::connect(socket, endPoints);
        asio::write(socket, asio::buffer("generate_pfp"));
        std::this_thread::sleep_for(std::chrono::seconds(60));
    }
}


int main() {
    asio::io_context ioContext;
    std::string pfpLink = "example";
    std::string host = "thenoahdevs.com";
    std::vector<std::thread> threads;
    
    for (int x = 0; x < 1; x++) { threads.emplace_back(activateAIServerListener); }
    for (int x = 0; x < 1; x++) { threads.emplace_back(initializePostGeneration); }
    for (auto& t : threads) {
        t.join();
    }
}
