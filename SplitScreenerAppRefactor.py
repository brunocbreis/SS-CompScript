from ss_backend import App


def main():
    app = App()

    app.build_layout()

    app.initialize_splitscreener()

    app.initialize_user_interface()

    app.run()


if __name__ == "__main__":
    main()
