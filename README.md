!["SplitScreener – Comp Script"](https://github.com/brunocbreis/SplitScreener/blob/master/imgs/ReadMeBanner_compscript.png)


 ![version: beta](https://img.shields.io/badge/version-beta-blue) ![works with DaVinci Resolve and Fusion Studio](https://img.shields.io/badge/works%20with-DaVinci%20Resolve%20%7C%20Fusion%20Studio-lightgrey)  [!["Buy Me A Coffee"](https://img.shields.io/badge/-buy_me_a%C2%A0coffee-gray?logo=buy-me-a-coffee)](https://www.buymeacoffee.com/brunoreis)
  

## Click, drag, split!
It's never been easier to create beautiful, consistent, and customizable split screen designs in DaVinci Resolve.

With SplitScreener's intuitive interface, anyone can build their own custom grid layout with the classic columns, rows, margins and gutter structure. From there, you just draw however many screens you want and they're automatically placed on your grid, while a node tree is dynamically generated as you design your SplitScreen. No Fusion knowledge required! **Seriously, none at all.**

### 🏋️ How it works
When you first open up the app, a default 12-by-6 grid is set up. You can customize canvas dimensions, margins, gutter and grid composition at any time. I do recommend the default 12-column setup, though, because 12 is awesome and can be subdivided in 2, 3, 4 and 6. 12 all the way! 🙌

When you're ready, you can click anywhere on the grid and drag to create a screen. **A blue rectangle will be drawn representing each screen** . It'll automatically position itself on the grid, and recompute its dimensions and position every time any setting is changed.

!["Clicking and dragging to create a Screen"](https://github.com/brunocbreis/SplitScreener/blob/master/imgs/Screenshot1_compscript.png)

As you can see below, whenever you create a screen, the corresponding nodes in the Fusion composition are automatically and dynamically generated for you. What you see in SplitScreener is exactly what you get in DaVinci Resolve! 

!["From SplitScreener to Fusion node tree to result"](https://github.com/brunocbreis/SplitScreener/blob/master/imgs/Screenshot2_flow_compscript.png)

### ⚙️ How to install
First, **open your Terminal application** and navigate to the `Comp` Scripts folder inside your **DaVinci Resolve** / **Fusion Studio** installation files directory. This is where all of your custom scripts can be placed for easy access from within the application, while you're in the Fusion page (or inside of Fusion Studio).

#### 🗂 Finding the Comp Scripts file path in your system
##### 🪟 Windows
DaVinci Resolve: `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Comp`

Fusion Studio: `C:\ProgramData\Blackmagic Design\Fusion Studio\Scripts\Comp`
##### 💻 MacOS
DaVinci Resolve: `[user]/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp`

Fusion Studio: `[user]/Library/Application Support/Blackmagic Design/Fusion Studio/Scripts/Comp`
#### 👯‍♂️ Cloning the repo with git
You can then use the following git command to clone the repo and install the latest version of *SplitScreener* in your system:

`git clone --recurse-submodules https://github.com/brunocbreis/SS-CompScript/ ./SplitScreener`

### 🏃‍♂️ Running the script
After installation, you're ready to *split some screens*! 🔪

From **DaVinci Resolve**, while in the Fusion Page, you can go to `Workspace > Scripts > Comp > SplitScreener` and run the *SplitScreener* app from there. In **Fusion Studio**, the *SplitScreener* folder will be directly under the `Scripts > Comp` menu.
