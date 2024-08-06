# README

## Python Security Automation Projects

Welcome to my repository containing various Python projects designed for security use case automations. These scripts are aimed at enhancing security operations through automation, covering a range of functionalities from Indicator of Compromise (IoC) management to firewall interactions.

## Table of Contents

- [Introduction](#introduction)
- [Projects](#projects)
  - [IoC Management](#ioc-management)
  - [Inventory Listing](#inventory-listing)
  - [VPN Whitelist Management](#vpn-whitelist-management)
  - [Fortigate Firewall Interactions](#fortigate-firewall-interactions)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Introduction

This repository contains a collection of Python scripts developed for automating various security-related tasks. These projects aim to streamline and enhance the efficiency of security operations by automating repetitive and time-consuming processes.

## Projects

### IoC Management

Scripts for managing Indicators of Compromise (IoCs), including:

- **IoC Collection**: Automated collection of IoCs from various threat intelligence sources.
- **IoC Enrichment**: Enhancing IoCs with additional context and threat intelligence.
- **IoC Integration**: Integrating IoCs with SIEM systems for improved detection and response.

### Inventory Listing

Scripts for automating the creation and maintenance of an inventory list of assets, including:

- **Asset Discovery**: Automated discovery of assets within the network.
- **Asset Inventory**: Maintaining an up-to-date inventory list with relevant details such as IP addresses, MAC addresses, and device types.

### VPN Whitelist Management

Scripts for managing VPN whitelists, including:

- **Whitelist Update**: Automating the process of adding and removing IP addresses from VPN whitelists.
- **Whitelist Monitoring**: Regular monitoring of whitelisted IPs to ensure compliance and security.

### Fortigate Firewall Interactions

Scripts for interacting with Fortigate firewalls, including:

- **Firewall Configuration**: Automating the configuration of firewall rules and policies.
- **Log Retrieval**: Automating the retrieval and analysis of firewall logs.
- **Threat Mitigation**: Automated response to detected threats by updating firewall rules.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/frenzydf/myPython.git
    cd myPython
    ```

2. Create and activate a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Each project has its own subdirectory with detailed instructions on how to use the scripts. Refer to the README files in the respective subdirectories for specific usage instructions.

## Contributing

Contributions are welcome! If you have ideas for improvements or new features, feel free to open an issue or submit a pull request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/Feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/Feature`)
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
