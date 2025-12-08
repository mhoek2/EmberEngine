class MyScript:
    value         : float     = export(1.0)
    boost         : float     = export(30.0)
    manipulate    : Transform = export()
    
    """Default script template"""
    def onStart( self ) -> None:
        self.camera = self.scene.getCamera()
        pass

    def onEnable( self ):
        pass

    def onDisable( self ):
        pass
        
    def onUpdate( self ) -> None:
        # print exported value for debugging purposes
        #print(self.value)

        keypress = self.key.get_pressed()
        velocity = self.value

        if keypress[pygame.K_u]:
            #self.gameObject.setActive(False)
            self.manipulate.position[1] += 0.5
            
        if keypress[pygame.K_LCTRL] or keypress[pygame.K_RCTRL]:
            velocity *= self.boost

        move = self.renderer.deltaTime * velocity

        if keypress[pygame.K_w]:
            self.transform.local_position[2] += move
            self.camera.transform.local_position[2] += move
        if keypress[pygame.K_s]:
            self.transform.local_position[2] -= move
            self.camera.transform.local_position[2] -= move
        if keypress[pygame.K_d]:
            self.transform.local_position[0] -= move
            self.camera.transform.local_position[0] -= move
        if keypress[pygame.K_a]:
            self.transform.local_position[0] += move
            self.camera.transform.local_position[0] += move